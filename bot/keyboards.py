from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def language_keyboard():
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("Русский", callback_data="lang_ru"),
        InlineKeyboardButton("English", callback_data="lang_en"),
        InlineKeyboardButton("ქართული", callback_data="lang_ge")
    )

def answer_keyboard():
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("A", callback_data="answer_A"),
        InlineKeyboardButton("B", callback_data="answer_B"),
        InlineKeyboardButton("C", callback_data="answer_C"),
        InlineKeyboardButton("D", callback_data="answer_D")
    )
