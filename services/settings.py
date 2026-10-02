from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Setting


async def get_setting(session: AsyncSession, key: str, default: str = "") -> str:
    item = await session.get(Setting, key)
    return item.value if item else default


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    item = await session.get(Setting, key)
    if item:
        item.value = value
    else:
        session.add(Setting(key=key, value=value))
    await session.commit()


async def get_settings(session: AsyncSession) -> dict[str, str]:
    result = await session.execute(select(Setting))
    return {item.key: item.value for item in result.scalars().all()}
