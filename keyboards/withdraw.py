from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def payout_methods(methods) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for method in methods:
        b.add(InlineKeyboardButton(text=method.name, callback_data=f"wd:method:{method.id}"))
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🏠 ГОЛОВНЕ МЕНЮ", callback_data="menu:home"))
    return b.as_markup()


def withdrawal_admin(withdrawal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ ВИПЛАЧЕНО", callback_data=f"adm:wdpaid:{withdrawal_id}"),
        InlineKeyboardButton(text="❌ ВІДХИЛИТИ", callback_data=f"adm:wdreject:{withdrawal_id}"),
    ]])
