from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def language_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора языка.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="Русский", callback_data="lang_ru")
    builder.button(text="English", callback_data="lang_en")
    builder.button(text="ქართული", callback_data="lang_ge")
    return builder.as_markup()


def category_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора категории.
    """
    builder = InlineKeyboardBuilder()
    categories = ["A", "B", "C", "D"]
    for category in categories:
        builder.button(text=f"Категория {category}", callback_data=f"category_{category}")
    return builder.as_markup()


def answer_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора ответа.
    """
    builder = InlineKeyboardBuilder()
    answers = ["A", "B", "C", "D"]
    for answer in answers:
        builder.button(text=answer, callback_data=f"answer_{answer}")
    return builder.as_markup()
