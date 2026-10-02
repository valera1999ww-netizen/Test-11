from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Transaction


async def get_history(session: AsyncSession, user_id: int, limit: int = 20) -> list[Transaction]:
    result = await session.execute(select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).limit(limit))
    return list(result.scalars().all())
