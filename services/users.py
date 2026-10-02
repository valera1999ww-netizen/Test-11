from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from aiogram import Bot
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Referral,
    Transaction,
    TransactionType,
    User,
)


# ============================================================
# НАЛАШТУВАННЯ КАНАЛУ
# ============================================================

CHANNEL_USERNAME = "@ua_2024k"


# ============================================================
# КОРИСТУВАЧ
# ============================================================

async def upsert_user(
    session: AsyncSession,
    tg_user,
    referrer_tg_id: Optional[int] = None,
) -> User:

    user = await session.scalar(
        select(User).where(
            User.telegram_id == tg_user.id
        )
    )

    # --------------------------------------------------------
    # НОВИЙ КОРИСТУВАЧ
    # --------------------------------------------------------

    if user is None:

        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Користувач",
        )

        # Реферал
        if (
            referrer_tg_id
            and referrer_tg_id != tg_user.id
        ):

            referrer = await session.scalar(
                select(User).where(
                    User.telegram_id == referrer_tg_id
                )
            )

            if referrer:
                user.referrer_id = referrer.id

        session.add(user)

        await session.commit()
        await session.refresh(user)

        return user

    # --------------------------------------------------------
    # ІСНУЮЧИЙ КОРИСТУВАЧ
    # --------------------------------------------------------

    user.username = tg_user.username

    if tg_user.first_name:
        user.first_name = tg_user.first_name

    user.last_active_at = datetime.now(timezone.utc)

    await session.commit()

    return user


# ============================================================
# ОТРИМАТИ КОРИСТУВАЧА
# ============================================================

async def get_user_by_tg_id(
    session: AsyncSession,
    telegram_id: int,
    lock: bool = False,
) -> Optional[User]:

    query = select(User).where(
        User.telegram_id == telegram_id
    )

    if lock:
        query = query.with_for_update()

    return await session.scalar(query)


# ============================================================
# ПЕРЕВІРКА ПІДПИСКИ
# ============================================================

async def verify_subscription(
    session: AsyncSession,
    bot: Bot,
    user: User,
) -> tuple[bool, str]:

    now = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # Користувач заблокований
    # --------------------------------------------------------

    if user.is_blocked:
        return False, "blocked"

    # --------------------------------------------------------
    # КОЖНА ПЕРЕВІРКА ЙДЕ НАПРЯМУ В TELEGRAM
    # --------------------------------------------------------
    # Кеш НЕ використовується.
    # --------------------------------------------------------

    try:

        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user.telegram_id,
        )

        status = member.status

        print(
            f"[SUB CHECK] "
            f"user={user.telegram_id} "
            f"channel={CHANNEL_USERNAME} "
            f"status={status}"
        )

        # ----------------------------------------------------
        # ЗВИЧАЙНИЙ ПІДПИСНИК
        # ----------------------------------------------------

        if status == "member":
            is_subscribed = True

        # ----------------------------------------------------
        # АДМІНІСТРАТОР
        # ----------------------------------------------------

        elif status == "administrator":
            is_subscribed = True

        # ----------------------------------------------------
        # ВЛАСНИК КАНАЛУ
        # ----------------------------------------------------

        elif status == "creator":
            is_subscribed = True

        # ----------------------------------------------------
        # RESTRICTED
        # ----------------------------------------------------
        # Telegram може повертати restricted.
        # Якщо is_member=True — користувач все одно є
        # учасником каналу.
        # ----------------------------------------------------

        elif status == "restricted":

            is_subscribed = bool(
                getattr(member, "is_member", False)
            )

        # ----------------------------------------------------
        # НЕ ПІДПИСАНИЙ / ВИЙШОВ
        # ----------------------------------------------------

        elif status == "left":
            is_subscribed = False

        # ----------------------------------------------------
        # ЗАБЛОКОВАНИЙ КАНАЛОМ
        # ----------------------------------------------------

        elif status == "kicked":
            is_subscribed = False

        # ----------------------------------------------------
        # НЕВІДОМИЙ СТАТУС
        # ----------------------------------------------------

        else:
            is_subscribed = False

        # ----------------------------------------------------
        # ЗБЕРІГАЄМО РЕЗУЛЬТАТ
        # ----------------------------------------------------

        user.is_subscribed = is_subscribed
        user.last_subscription_check = now

        await session.commit()

        print(
            f"[SUB RESULT] "
            f"user={user.telegram_id} "
            f"subscribed={is_subscribed}"
        )

        return is_subscribed, "live"

    # --------------------------------------------------------
    # ПОМИЛКА TELEGRAM API
    # --------------------------------------------------------

    except Exception as error:

        print(
            f"[SUB CHECK ERROR] "
            f"user={user.telegram_id} "
            f"channel={CHANNEL_USERNAME} "
            f"error={repr(error)}"
        )

        user.is_subscribed = False
        user.last_subscription_check = now

        await session.commit()

        return False, "error"


# ============================================================
# СТАРТОВИЙ БОНУС + РЕФЕРАЛ
# ============================================================

async def grant_start_bonus_and_referral(
    session: AsyncSession,
    user: User,
) -> tuple[bool, int]:

    locked_user = await get_user_by_tg_id(
        session,
        user.telegram_id,
        lock=True,
    )

    if locked_user is None:
        return False, 0

    bonus_granted = False
    referral_spin_granted = 0

    # ========================================================
    # СТАРТОВИЙ СПІН
    # ========================================================

    start_bonus_exists = await session.scalar(
        select(Transaction.id).where(
            Transaction.user_id == locked_user.id,
            Transaction.description == "START_BONUS",
        )
    )

    if start_bonus_exists is None:

        locked_user.spins += 1

        session.add(
            Transaction(
                user_id=locked_user.id,
                tx_type=TransactionType.REFERRAL_SPIN,
                amount=Decimal("0.00"),
                balance_after=locked_user.balance,
                description="START_BONUS",
            )
        )

        bonus_granted = True

    # ========================================================
    # РЕФЕРАЛ
    # ========================================================

    if locked_user.referrer_id:

        referral_exists = await session.scalar(
            select(Referral).where(
                Referral.referred_user_id == locked_user.id
            )
        )

        if referral_exists is None:

            referral = Referral(
                referrer_id=locked_user.referrer_id,
                referred_user_id=locked_user.id,
            )

            session.add(referral)

            referrer = await session.scalar(
                select(User)
                .where(
                    User.id == locked_user.referrer_id
                )
                .with_for_update()
            )

            if referrer:

                referrer.referral_count += 1

                # Кожні 3 реферали = +1 спін
                if referrer.referral_count % 3 == 0:

                    referrer.spins += 1

                    session.add(
                        Transaction(
                            user_id=referrer.id,
                            tx_type=TransactionType.REFERRAL_SPIN,
                            amount=Decimal("0.00"),
                            balance_after=referrer.balance,
                            description="REFERRAL_SPIN_BONUS +1",
                        )
                    )

                    referral_spin_granted = 1

    await session.commit()

    return bonus_granted, referral_spin_granted


# ============================================================
# ПРОФІЛЬ
# ============================================================

async def get_profile(
    session: AsyncSession,
    telegram_id: int,
) -> Optional[User]:

    return await get_user_by_tg_id(
        session,
        telegram_id,
    )


# ============================================================
# КІЛЬКІСТЬ КОРИСТУВАЧІВ
# ============================================================

async def count_users(
    session: AsyncSession,
) -> int:

    result = await session.scalar(
        select(func.count())
        .select_from(User)
    )

    return int(result or 0)


# ============================================================
# АКТИВНІ КОРИСТУВАЧІ
# ============================================================

async def count_active_users(
    session: AsyncSession,
    hours: int = 24,
) -> int:

    threshold = (
        datetime.now(timezone.utc)
        - timedelta(hours=hours)
    )

    result = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.last_active_at >= threshold
        )
    )

    return int(result or 0)


# ============================================================
# НОВІ КОРИСТУВАЧІ
# ============================================================

async def count_new_users(
    session: AsyncSession,
    days: int,
) -> int:

    threshold = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    )

    result = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.created_at >= threshold
        )
    )

    return int(result or 0)
