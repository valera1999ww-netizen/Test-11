from __future__ import annotations

import re

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.common import main_menu, sub_gate
from services.settings import get_setting
from utils.config import Config
from services.users import (
    grant_start_bonus_and_referral,
    get_user_by_tg_id,
    upsert_user,
    verify_subscription,
)

router = Router()

# Твій Telegram-канал
CHANNEL_USERNAME = "@ua_2024k"


@router.message(CommandStart())
async def start_handler(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    config: Config,
):
    is_admin = message.from_user.id in config.admin_ids

    # Отримуємо реферала
    payload = ""
    parts = (message.text or "").split(maxsplit=1)

    if len(parts) == 2:
        payload = parts[1].strip()

    referrer_tg_id = None

    match = re.fullmatch(r"ref_(\d+)", payload)

    if match:
        referrer_tg_id = int(match.group(1))

    # Створюємо / оновлюємо користувача
    user = await upsert_user(
        session,
        message.from_user,
        referrer_tg_id,
    )

    # Перевіряємо підписку
    ok, _ = await verify_subscription(
        session,
        bot,
        user,
    )

    # Назва бота з налаштувань
    bot_name = await get_setting(
        session,
        "bot_name",
        "Reward Spin",
    )

    # Посилання саме на твій канал
    channel_url = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"

    # Якщо НЕ підписаний
    if not ok:
        await message.answer(
            f"🎁 <b>ВІТАЄМО У {bot_name.upper()}!</b>\n\n"
            "💰 Тут ти можеш отримувати реальні винагороди за прості дії.\n\n"
            "🎁 <b>Твій стартовий бонус — 1 безкоштовний спін!</b>\n\n"
            "Щоб активувати його, підпишись на канал "
            "та підтвердь підписку:",
            reply_markup=sub_gate(channel_url),
        )
        return

    # Якщо вже підписаний
    bonus, ref_spin = await grant_start_bonus_and_referral(
        session,
        user,
    )

    extra = ""

    if bonus:
        extra += (
            "\n🎁 Тобі нараховано "
            "<b>1 безкоштовний спін</b>."
        )

    if ref_spin:
        extra += (
            "\n👥 За 3 нових реферали отримано "
            "<b>+1 спін</b>."
        )

    await message.answer(
        f"🎉 <b>З РЕЄСТРАЦІЄЮ У {bot_name.upper()}!</b>\n\n"
        "✨ Усі розділи доступні нижче."
        + extra,
        reply_markup=main_menu(is_admin),
    )


@router.callback_query(F.data == "sub:check")
async def subscription_check(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    config: Config,
):
    is_admin = callback.from_user.id in config.admin_ids

    # Знаходимо користувача
    user = await get_user_by_tg_id(
        session,
        callback.from_user.id,
    )

    if user is None:
        await callback.answer(
            "Спочатку натисни /start",
            show_alert=True,
        )
        return

    # Перевіряємо підписку
    ok, _ = await verify_subscription(
        session,
        bot,
        user,
    )

    if not ok:
        await callback.answer(
            "❌ Підписка не підтверджена.\n\n"
            "Спочатку підпишись на канал @ua_2024k.",
            show_alert=True,
        )
        return

    # Видаємо стартовий бонус
    bonus, ref_spin = await grant_start_bonus_and_referral(
        session,
        user,
    )

    text = (
        "🎉 <b>ПІДПИСКУ ПІДТВЕРДЖЕНО!</b>\n\n"
    )

    if bonus:
        text += (
            "🎁 Тобі нараховано "
            "<b>1 безкоштовний спін</b>."
        )
    else:
        text += (
            "✅ Доступ уже був активований раніше."
        )

    if ref_spin:
        text += (
            "\n👥 Додатково: "
            "<b>+1 спін за рефералів</b>."
        )

    await callback.message.edit_text(
        text,
        reply_markup=main_menu(is_admin),
    )

    await callback.answer("✅ Готово")
