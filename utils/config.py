from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def parse_ints(value: str) -> set[int]:
    return {int(x.strip()) for x in value.split(",") if x.strip()}


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    web_host: str
    web_port: int
    broadcast_delay: float


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is required")
    return Config(
        bot_token=token,
        admin_ids=parse_ints(os.getenv("ADMIN_IDS", "")),
        web_host=os.getenv("WEB_HOST", "0.0.0.0"),
        web_port=int(os.getenv("PORT", os.getenv("WEB_PORT", "10000"))),
        broadcast_delay=float(os.getenv("BROADCAST_DELAY", "0.08")),
    )
