from __future__ import annotations

from decimal import Decimal
import random

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Prize, Spin, Transaction, TransactionType, User


async def choose_prize(session: AsyncSession) -> Prize:
    result = await session.execute(select(Prize).where(Prize.is_active.is_(True)).order_by(Prize.amount))
    prizes = list(result.scalars().all())
    if not prizes:
        raise ValueError("No active prizes configured")
    total = sum((Decimal(p.chance) for p in prizes), Decimal("0"))
    if total != Decimal("100"):
        raise ValueError(f"Prize chances total must equal 100, got {total}")
    pick = Decimal(str(random.uniform(0, 100)))
    cursor = Decimal("0")
    for prize in prizes:
        cursor += Decimal(prize.chance)
        if pick <= cursor:
            return prize
    return prizes[-1]


async def consume_spin_and_reward(session: AsyncSession, telegram_id: int) -> Decimal:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
    if user is None:
        raise ValueError("User not found")
    if user.spins <= 0:
        raise ValueError("No spins")

    prize = await choose_prize(session)
    user.spins -= 1
    amount = Decimal(prize.amount)
    user.balance = Decimal(user.balance) + amount
    user.total_won = Decimal(user.total_won) + amount
    session.add(Spin(user_id=user.id, amount=amount, source="free"))
    session.add(Transaction(user_id=user.id, tx_type=TransactionType.SPIN_PRIZE, amount=amount, balance_after=user.balance, description=f"Спін +{amount} грн"))
    await session.commit()
    return amount


async def add_spins(session: AsyncSession, telegram_id: int, amount: int) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
    if not user:
        raise ValueError("Користувача не знайдено")
    new_value = user.spins + amount
    if new_value < 0:
        raise ValueError("Недостатньо спінів")
    user.spins = new_value
    await session.commit()
    return user


async def credit_balance(session: AsyncSession, telegram_id: int, amount: Decimal, tx_type: TransactionType, description: str) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
    if not user:
        raise ValueError("Користувача не знайдено")
    user.balance = Decimal(user.balance) + amount
    session.add(Transaction(user_id=user.id, tx_type=tx_type, amount=amount, balance_after=user.balance, description=description))
    await session.commit()
    return user
