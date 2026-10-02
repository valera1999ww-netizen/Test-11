from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse
from decimal import Decimal
from typing import Optional

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CompletionStatus, Task, TaskCompletion, TaskType, Transaction, TransactionType, User
from services.settings import get_setting


async def get_active_tasks(session: AsyncSession, user_id: int) -> list[Task]:
    completed = select(TaskCompletion.task_id).where(
        TaskCompletion.task_id == Task.id,
        TaskCompletion.user_id == user_id,
        TaskCompletion.status.in_([CompletionStatus.COMPLETED, CompletionStatus.PENDING_REVIEW]),
    )
    result = await session.execute(
        select(Task)
        .where(Task.is_active.is_(True))
        .where(~completed.exists())
        .order_by(Task.sort_order.asc(), Task.id.asc())
    )
    return list(result.scalars().all())


async def get_task(session: AsyncSession, task_id: int) -> Optional[Task]:
    return await session.get(Task, task_id)


async def _channel_membership_ok(session: AsyncSession, bot: Bot, user: User) -> bool:
    chat_id = await get_setting(session, "channel_chat_id", "")
    username = await get_setting(session, "channel_username", "")
    chat_id = chat_id or (f"@{username.lstrip('@')}" if username else "")
    if not chat_id:
        return False
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user.telegram_id)
        return member.status in {"member", "administrator", "creator"}
    except Exception:
        return False


async def _task_target_membership_ok(session: AsyncSession, bot: Bot, user: User, task: Task) -> bool:
    if task.task_type not in {TaskType.SUBSCRIBE, TaskType.VIEW_CHANNEL}:
        return True
    # Telegram does not expose a reliable signal that a user read a particular post.
    # For these task types we therefore verify membership in the public target channel only.
    parsed = urlparse(task.link)
    channel = parsed.path.strip("/").split("/")[0] if parsed.netloc in {"t.me", "telegram.me", "www.t.me"} else ""
    if not channel or channel.startswith("+"):
        return False
    try:
        member = await bot.get_chat_member(chat_id=f"@{channel}", user_id=user.telegram_id)
        return member.status in {"member", "administrator", "creator"}
    except Exception:
        return False


async def complete_task(
    session: AsyncSession,
    bot: Bot,
    telegram_id: int,
    task_id: int,
) -> tuple[str, Decimal]:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
    task = await session.scalar(select(Task).where(Task.id == task_id).with_for_update())
    if user is None or task is None or not task.is_active:
        raise ValueError("Завдання недоступне")

    existing = await session.scalar(select(TaskCompletion).where(TaskCompletion.task_id == task_id, TaskCompletion.user_id == user.id))
    if existing:
        if existing.status == CompletionStatus.COMPLETED:
            raise ValueError("Завдання вже виконано")
        if existing.status == CompletionStatus.PENDING_REVIEW:
            raise ValueError("Завдання вже очікує перевірки")
        await session.delete(existing)
        await session.flush()

    if task.max_completions is not None and task.completion_count >= task.max_completions:
        raise ValueError("Ліміт виконань цього завдання вже вичерпано")

    if task.task_type in {TaskType.SUBSCRIBE, TaskType.VIEW_CHANNEL}:
        if not await _task_target_membership_ok(session, bot, user, task):
            raise ValueError("Не вдалося підтвердити підписку на потрібний канал")
        status = CompletionStatus.COMPLETED
    elif task.requires_verification:
        status = CompletionStatus.PENDING_REVIEW
    else:
        status = CompletionStatus.COMPLETED

    completion = TaskCompletion(task_id=task.id, user_id=user.id, status=status, reward=task.reward)
    session.add(completion)
    if status == CompletionStatus.COMPLETED:
        reward = Decimal(task.reward)
        user.balance = Decimal(user.balance) + reward
        user.total_won = Decimal(user.total_won) + reward
        user.task_count += 1
        task.completion_count += 1
        session.add(Transaction(
            user_id=user.id,
            tx_type=TransactionType.TASK_REWARD,
            amount=reward,
            balance_after=user.balance,
            description=f"Завдання +{reward} грн: {task.title}",
        ))
        await session.commit()
        return "completed", reward

    await session.commit()
    return "pending", Decimal(task.reward)


async def review_task_completion(session: AsyncSession, completion_id: int, approve: bool) -> tuple[CompletionStatus, Decimal, int]:
    completion = await session.scalar(select(TaskCompletion).where(TaskCompletion.id == completion_id).with_for_update())
    if completion is None:
        raise ValueError("Заявку не знайдено")
    if completion.status != CompletionStatus.PENDING_REVIEW:
        raise ValueError("Заявка вже опрацьована")

    if not approve:
        completion.status = CompletionStatus.REJECTED
        completion.reviewed_at = datetime.now(timezone.utc)
        await session.commit()
        return CompletionStatus.REJECTED, Decimal("0"), completion.user_id

    task = await session.scalar(select(Task).where(Task.id == completion.task_id).with_for_update())
    user = await session.scalar(select(User).where(User.id == completion.user_id).with_for_update())
    if task is None or user is None:
        raise ValueError("Пов'язані дані не знайдено")
    if task.max_completions is not None and task.completion_count >= task.max_completions:
        raise ValueError("Ліміт виконань уже вичерпано")

    reward = Decimal(completion.reward)
    user.balance = Decimal(user.balance) + reward
    user.total_won = Decimal(user.total_won) + reward
    user.task_count += 1
    task.completion_count += 1
    completion.status = CompletionStatus.COMPLETED
    completion.reviewed_at = datetime.now(timezone.utc)
    session.add(Transaction(user_id=user.id, tx_type=TransactionType.TASK_REWARD, amount=reward, balance_after=user.balance, description=f"Перевірене завдання +{reward} грн: {task.title}"))
    await session.commit()
    return CompletionStatus.COMPLETED, reward, user.id


async def get_pending_completions(session: AsyncSession, limit: int = 20) -> list[tuple[TaskCompletion, Task, User]]:
    result = await session.execute(
        select(TaskCompletion, Task, User)
        .join(Task, Task.id == TaskCompletion.task_id)
        .join(User, User.id == TaskCompletion.user_id)
        .where(TaskCompletion.status == CompletionStatus.PENDING_REVIEW)
        .order_by(TaskCompletion.created_at.asc())
        .limit(limit)
    )
    return list(result.all())
