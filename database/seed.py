from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Prize, PayoutMethod, Setting

DEFAULT_PRIZES = [
    (10, Decimal("30")),
    (20, Decimal("25")),
    (30, Decimal("20")),
    (50, Decimal("12")),
    (100, Decimal("7")),
    (200, Decimal("4")),
    (300, Decimal("2")),
]

DEFAULT_SETTINGS = {
    "bot_name": "Reward Spin",
    "min_withdrawal": "50",
    "channel_username": "",
    "channel_chat_id": "",
    "support_username": "ua_101",
}


async def seed_defaults(session: AsyncSession) -> None:
    result = await session.execute(select(Prize).order_by(Prize.amount))
    if not result.scalars().first():
        session.add_all([Prize(amount=Decimal(amount), chance=chance) for amount, chance in DEFAULT_PRIZES])

    result = await session.execute(select(PayoutMethod).limit(1))
    if not result.scalars().first():
        session.add_all([
            PayoutMethod(name="💳 Банківська картка", kind="card"),
            PayoutMethod(name="💳 Інший доступний спосіб", kind="text"),
        ])

    for key, value in DEFAULT_SETTINGS.items():
        setting = await session.get(Setting, key)
        if setting is None:
            session.add(Setting(key=key, value=value))
    await session.commit()
