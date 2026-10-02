from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI
import uvicorn

from database.db import engine, init_db, SessionLocal
from database.seed import seed_defaults
from handlers import admin as admin_handlers
from handlers import start as start_handlers
from handlers import user as user_handlers
from middlewares.db import DBSessionMiddleware
from middlewares.throttling import SimpleRateLimitMiddleware
from utils.config import load_config

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("reward-bot")

app = FastAPI(title="Reward Telegram Bot", docs_url=None, redoc_url=None)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


async def run_web(config) -> None:
    server = uvicorn.Server(uvicorn.Config(app, host=config.web_host, port=config.web_port, log_level="warning"))
    await server.serve()


async def main() -> None:
    config = load_config()
    await init_db()
    async with SessionLocal() as session:
        await seed_defaults(session)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(DBSessionMiddleware())
    dp.callback_query.middleware(DBSessionMiddleware())
    dp.message.middleware(SimpleRateLimitMiddleware(0.35))
    dp.callback_query.middleware(SimpleRateLimitMiddleware(0.35))

    dp.include_router(start_handlers.router)
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    me = await bot.get_me()
    logger.info("Starting @%s", me.username)
    if not config.admin_ids:
        logger.warning("ADMIN_IDS is empty; admin panel will be inaccessible")

    try:
        # Long polling must own the update stream; remove any previously configured webhook.
        await bot.delete_webhook(drop_pending_updates=False)
        await asyncio.gather(
            dp.start_polling(bot, config=config, allowed_updates=dp.resolve_used_update_types()),
            run_web(config),
        )
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopped")
