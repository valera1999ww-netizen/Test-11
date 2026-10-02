from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for text, data in [
        ("📊 Статистика", "adm:stats"), ("👥 Користувачі", "adm:users"),
        ("💰 Баланси", "adm:balance"), ("🎁 Видача спінів", "adm:spins"),
        ("💵 Видача грн", "adm:credit"), ("🎯 Завдання", "adm:tasks"),
        ("📢 Розсилка", "adm:broadcast"), ("💸 Виплати", "adm:withdrawals"),
        ("🎲 Шанси призів", "adm:chances"), ("📢 Канали", "adm:channels"),
        ("⚙️ Налаштування", "adm:settings"), ("📜 Логи", "adm:logs"),
    ]:
        b.add(InlineKeyboardButton(text=text, callback_data=data))
    b.adjust(2)
    b.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="menu:home"))
    return b.as_markup()


def confirm(action: str, cancel: str = "adm:open") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ ПІДТВЕРДИТИ", callback_data=action),
        InlineKeyboardButton(text="❌ СКАСУВАТИ", callback_data=cancel),
    ]])
