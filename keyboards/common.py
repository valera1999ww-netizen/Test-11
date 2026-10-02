from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def sub_gate(url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.add(InlineKeyboardButton(text="📢 ПІДПИСАТИСЯ НА КАНАЛ", url=url))
    b.add(InlineKeyboardButton(text="✅ ПЕРЕВІРИТИ ПІДПИСКУ", callback_data="sub:check"))
    b.adjust(1)
    return b.as_markup()


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🎁 Отримати приз", callback_data="menu:spin"), InlineKeyboardButton(text="📋 Завдання", callback_data="menu:tasks"))
    b.row(InlineKeyboardButton(text="💰 Мій баланс", callback_data="menu:profile"), InlineKeyboardButton(text="👥 Запросити друзів", callback_data="menu:ref"))
    b.row(InlineKeyboardButton(text="💸 Вивести кошти", callback_data="menu:withdraw"), InlineKeyboardButton(text="📜 Історія", callback_data="menu:history"))
    b.row(InlineKeyboardButton(text="📖 Правила", callback_data="menu:rules"), InlineKeyboardButton(text="📞 Підтримка", callback_data="menu:support"))
    if is_admin:
        b.row(InlineKeyboardButton(text="👑 Адмін-панель", callback_data="admin:open"))
    return b.as_markup()


def back_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 ГОЛОВНЕ МЕНЮ", callback_data="menu:home")]])
