from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AdminLog, PayoutMethod, Prize, User, Withdrawal


async def add_admin_log(session: AsyncSession, admin_id: int, action: str, target_user_id: int | None = None, details: str = "") -> None:
    session.add(AdminLog(admin_telegram_id=admin_id, action=action, target_user_id=target_user_id, details=details))
    await session.commit()


async def get_prizes(session: AsyncSession) -> list[Prize]:
    result = await session.execute(select(Prize).order_by(Prize.amount))
    return list(result.scalars().all())


async def set_prize_chance(session: AsyncSession, prize_id: int, chance: Decimal) -> None:
    prize = await session.get(Prize, prize_id)
    if not prize:
        raise ValueError("Приз не знайдено")
    if chance < 0 or chance > 100:
        raise ValueError("Шанс повинен бути від 0 до 100")
    prize.chance = chance
    result = await session.execute(select(Prize).where(Prize.is_active.is_(True)))
    total = sum((Decimal(x.chance) for x in result.scalars().all()), Decimal("0"))
    if total != Decimal("100"):
        await session.rollback()
        raise ValueError(f"Після зміни сума шансів = {total}, потрібно 100")
    await session.commit()


async def list_recent_users(session: AsyncSession, limit: int = 20) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def get_pending_withdrawals(session: AsyncSession, limit: int = 20):
    result = await session.execute(select(Withdrawal).where(Withdrawal.status == "pending").order_by(Withdrawal.created_at.asc()).limit(limit))
    return list(result.scalars().all())


async def list_methods(session: AsyncSession):
    result = await session.execute(select(PayoutMethod).order_by(PayoutMethod.id))
    return list(result.scalars().all())


async def set_method_active(session: AsyncSession, method_id: int, active: bool) -> None:
    method = await session.get(PayoutMethod, method_id)
    if not method:
        raise ValueError("Спосіб не знайдено")
    method.is_active = active
    await session.commit()
