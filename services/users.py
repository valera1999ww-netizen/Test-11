from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from aiogram import Bot
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Referral, Transaction, TransactionType, User
from services.settings import get_setting


async def upsert_user(
    session: AsyncSession,
    tg_user,
    referrer_tg_id: Optional[int] = None
) -> User:

    user = await session.scalar(
        select(User).where(User.telegram_id == tg_user.id)
    )

    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Користувач"
        )

        if referrer_tg_id and referrer_tg_id != tg_user.id:
            referrer = await session.scalar(
                select(User).where(User.telegram_id == referrer_tg_id)
            )

            if referrer:
                user.referrer_id = referrer.id

        session.add(user)
        await session.commit()
        await session.refresh(user)

    else:
        user.username = tg_user.username
        user.first_name = tg_user.first_name or user.first_name
        user.last_active_at = datetime.now(timezone.utc)

        await session.commit()

    return user


async def get_user_by_tg_id(
    session: AsyncSession,
    telegram_id: int,
    lock: bool = False
) -> Optional[User]:

    stmt = select(User).where(User.telegram_id == telegram_id)

    if lock:
        stmt = stmt.with_for_update()

    return await session.scalar(stmt)


async def verify_subscription(
    session: AsyncSession,
    bot: Bot,
    user: User
) -> tuple[bool, str]:

    now = datetime.now(timezone.utc)

    if user.is_blocked:
        return False, "blocked"

    # ВАЖЛИВО:
    # більше НЕ використовуємо кеш 45 секунд.
    # Кожне натискання "Перевірити підписку"
    # робить реальну перевірку Telegram.

    chat_id = await get_setting(
        session,
        "channel_chat_id",
        ""
    )

    username = await get_setting(
        session,
        "channel_username",
        ""
    )

    # Якщо є числовий ID каналу — використовуємо його.
    # Для приватного каналу це ОБОВ'ЯЗКОВО.
    if not chat_id:
        if username:
            chat_id = f"@{username.lstrip('@')}"
        else:
            user.is_subscribed = False
            user.last_subscription_check = now

            await session.commit()

            return False, "not_configured"

    try:
        member = await bot.get_chat_member(
            chat_id=chat_id,
            user_id=user.telegram_id
        )

        is_sub = member.status in {
            "member",
            "administrator",
            "creator"
        }

    except Exception as e:
        print(
            f"[SUBSCRIPTION ERROR] "
            f"user={user.telegram_id} "
            f"chat_id={chat_id} "
            f"error={e}"
        )

        is_sub = False

    user.is_subscribed = is_sub
    user.last_subscription_check = now

    await session.commit()

    return is_sub, "live"


async def grant_start_bonus_and_referral(
    session: AsyncSession,
    user: User
) -> tuple[bool, int]:

    locked = await get_user_by_tg_id(
        session,
        user.telegram_id,
        lock=True
    )

    if locked is None:
        return False, 0

    bonus_granted = False
    referral_spin_granted = 0

    marker = await session.scalar(
        select(Transaction.id).where(
            Transaction.user_id == locked.id,
            Transaction.description == "START_BONUS"
        )
    )

    if marker is None:
        locked.spins += 1

        session.add(
            Transaction(
                user_id=locked.id,
                tx_type=TransactionType.REFERRAL_SPIN,
                amount=Decimal("0.00"),
                balance_after=locked.balance,
                description="START_BONUS",
            )
        )

        bonus_granted = True

    if locked.referrer_id:

        existing = await session.scalar(
            select(Referral).where(
                Referral.referred_user_id == locked.id
            )
        )

        if existing is None:

            ref = Referral(
                referrer_id=locked.referrer_id,
                referred_user_id=locked.id
            )

            session.add(ref)

            referrer = await session.scalar(
                select(User)
                .where(User.id == locked.referrer_id)
                .with_for_update()
            )

            if referrer:

                referrer.referral_count += 1

                if referrer.referral_count % 3 == 0:

                    referrer.spins += 1

                    session.add(
                        Transaction(
                            user_id=referrer.id,
                            tx_type=TransactionType.REFERRAL_SPIN,
                            amount=Decimal("0.00"),
                            balance_after=referrer.balance,
                            description="REFERRAL_SPIN_BONUS +1",
                        )
                    )

                    referral_spin_granted = 1

    await session.commit()

    return bonus_granted, referral_spin_granted


async def get_profile(
    session: AsyncSession,
    telegram_id: int
) -> Optional[User]:

    return await get_user_by_tg_id(
        session,
        telegram_id
    )


async def count_users(session: AsyncSession) -> int:

    return int(
        await session.scalar(
            select(func.count()).select_from(User)
        ) or 0
    )


async def count_active_users(
    session: AsyncSession,
    hours: int = 24
) -> int:

    threshold = (
        datetime.now(timezone.utc)
        - timedelta(hours=hours)
    )

    return int(
        await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.last_active_at >= threshold)
        ) or 0
    )


async def count_new_users(
    session: AsyncSession,
    days: int
) -> int:

    threshold = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    )

    return int(
        await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.created_at >= threshold)
        ) or 0
    )
