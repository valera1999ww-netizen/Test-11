from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PayoutMethod, Transaction, TransactionType, User, Withdrawal, WithdrawalStatus
from services.settings import get_setting


async def list_payout_methods(session: AsyncSession) -> list[PayoutMethod]:
    result = await session.execute(select(PayoutMethod).where(PayoutMethod.is_active.is_(True)).order_by(PayoutMethod.id))
    return list(result.scalars().all())


async def get_payout_method(session: AsyncSession, method_id: int) -> Optional[PayoutMethod]:
    return await session.get(PayoutMethod, method_id)


async def create_withdrawal(session: AsyncSession, telegram_id: int, method_id: int, amount: Decimal, destination: str) -> Withdrawal:
    if amount <= 0:
        raise ValueError("Сума повинна бути більше 0")
    min_value = Decimal(await get_setting(session, "min_withdrawal", "50"))
    if amount < min_value:
        raise ValueError(f"Мінімальна виплата — {min_value:.2f} грн")

    user = await session.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
    method = await session.scalar(select(PayoutMethod).where(PayoutMethod.id == method_id, PayoutMethod.is_active.is_(True)))
    if not user or not method:
        raise ValueError("Спосіб виплати недоступний")
    if Decimal(user.balance) < amount:
        raise ValueError("Недостатньо коштів на балансі")

    user.balance = Decimal(user.balance) - amount
    withdrawal = Withdrawal(user_id=user.id, payout_method_id=method.id, amount=amount, destination=destination, status=WithdrawalStatus.PENDING)
    session.add(withdrawal)
    session.add(Transaction(user_id=user.id, tx_type=TransactionType.WITHDRAWAL, amount=-amount, balance_after=user.balance, description=f"Резерв виплати -{amount} грн"))
    await session.commit()
    await session.refresh(withdrawal)
    return withdrawal


async def get_withdrawal(session: AsyncSession, withdrawal_id: int) -> Optional[Withdrawal]:
    return await session.get(Withdrawal, withdrawal_id)


async def process_withdrawal(session: AsyncSession, withdrawal_id: int, status: WithdrawalStatus, admin_note: str = "") -> Withdrawal:
    withdrawal = await session.scalar(select(Withdrawal).where(Withdrawal.id == withdrawal_id).with_for_update())
    if not withdrawal:
        raise ValueError("Заявку не знайдено")
    if withdrawal.status != WithdrawalStatus.PENDING:
        raise ValueError("Ця заявка вже опрацьована")

    user = await session.scalar(select(User).where(User.id == withdrawal.user_id).with_for_update())
    if not user:
        raise ValueError("Користувача не знайдено")

    withdrawal.status = status
    withdrawal.admin_note = admin_note or None
    withdrawal.processed_at = datetime.now(timezone.utc)
    if status == WithdrawalStatus.PAID:
        user.total_paid = Decimal(user.total_paid) + Decimal(withdrawal.amount)
    elif status == WithdrawalStatus.REJECTED:
        amount = Decimal(withdrawal.amount)
        user.balance = Decimal(user.balance) + amount
        session.add(Transaction(user_id=user.id, tx_type=TransactionType.WITHDRAWAL_REFUND, amount=amount, balance_after=user.balance, description=f"Повернення виплати +{amount} грн"))
    else:
        raise ValueError("Невідомий статус")

    await session.commit()
    return withdrawal
