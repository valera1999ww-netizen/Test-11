from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class SimpleRateLimitMiddleware(BaseMiddleware):
    def __init__(self, interval: float = 0.7):
        self.interval = interval
        self.last_seen = defaultdict(float)

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        tg_user = getattr(event, "from_user", None)
        if tg_user:
            now = time.monotonic()
            last = self.last_seen[tg_user.id]
            if now - last < self.interval:
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Не так швидко…", show_alert=False)
                elif isinstance(event, Message):
                    await event.answer("⏳ Не так швидко…")
                return
            self.last_seen[tg_user.id] = now
        return await handler(event, data)
