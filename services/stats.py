from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CompletionStatus, Referral, TaskCompletion, Transaction, TransactionType, User, Withdrawal, WithdrawalStatus


async def dashboard(session: AsyncSession) -> dict[str, Decimal | int]:
    now = datetime.now(timezone.utc)
    day = now - timedelta(days=1)
    week = now - timedelta(days=7)
    total_users = int(await session.scalar(select(func.count()).select_from(User)) or 0)
    active = int(await session.scalar(select(func.count()).select_from(User).where(User.last_active_at >= day)) or 0)
    new_today = int(await session.scalar(select(func.count()).select_from(User).where(User.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0))) or 0)
    new_week = int(await session.scalar(select(func.count()).select_from(User).where(User.created_at >= week)) or 0)
    spins = int(await session.scalar(select(func.count()).select_from(Transaction).where(Transaction.tx_type == TransactionType.SPIN_PRIZE)) or 0)
    credited = Decimal(await session.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.amount > 0)) or 0)
    paid = Decimal(await session.scalar(select(func.coalesce(func.sum(Withdrawal.amount), 0)).where(Withdrawal.status == WithdrawalStatus.PAID)) or 0)
    tasks = int(await session.scalar(select(func.count()).select_from(TaskCompletion).where(TaskCompletion.status == CompletionStatus.COMPLETED)) or 0)
    refs = int(await session.scalar(select(func.count()).select_from(Referral)) or 0)
    return {"total_users": total_users, "active": active, "new_today": new_today, "new_week": new_week, "spins": spins, "credited": credited, "paid": paid, "tasks": tasks, "refs": refs}
