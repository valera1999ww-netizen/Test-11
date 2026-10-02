from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def task_card(task_id: int, link: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.add(InlineKeyboardButton(text="🔗 ВІДКРИТИ", url=link))
    b.add(InlineKeyboardButton(text="✅ ПЕРЕВІРИТИ", callback_data=f"task:check:{task_id}"))
    b.adjust(1)
    return b.as_markup()


def task_review(completion_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ СХВАЛИТИ", callback_data=f"adm:taskapprove:{completion_id}"),
        InlineKeyboardButton(text="❌ ВІДХИЛИТИ", callback_data=f"adm:taskreject:{completion_id}"),
    ]])
