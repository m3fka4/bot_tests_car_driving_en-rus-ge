from aiogram import types, Dispatcher, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from magic_filter import F
from .keyboards import language_keyboard, answer_keyboard
from .database import init_db

# Словарь для хранения состояния пользователей
user_state = {}

# Хранение текущего теста пользователя
user_tests = {}


async def start_handler(message: types.Message):
    """
    Обработчик команды /start.
    """
    await message.answer(
        "Добро пожаловать в бот для подготовки к грузинскому тесту на права!\n"
        "Выберите язык:",
        reply_markup=language_keyboard()
    )


async def language_choice(callback_query: types.CallbackQuery):
    """
    Обработчик выбора языка.
    """
    user_id = callback_query.from_user.id
    lang = callback_query.data.split("_")[1]  # Получаем 'ru', 'en' или 'ge'

    user_state[user_id] = {'lang': lang}  # Сохраняем язык пользователя

    try:
        await callback_query.message.edit_text(
            f"Вы выбрали язык: {'Русский' if lang == 'ru' else 'English' if lang == 'en' else 'ქართული'}\n"
            "Выберите категорию прав (например, A, B, C, D):"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass  # Игнорируем, если сообщение не изменилось
        else:
            raise


async def category_choice(message: types.Message):
    """
    Обработчик выбора категории прав.
    """
    user_id = message.from_user.id
    category = message.text.upper()  # Преобразуем в верхний регистр

    # Проверяем, указал ли пользователь язык ранее
    if user_id not in user_state or 'lang' not in user_state[user_id]:
        await message.reply("Сначала выберите язык. Напишите /start.")
        return

    user_state[user_id]['category'] = category
    await message.answer(
        f"Вы выбрали категорию: {category}.\n"
        "Начнем тест! Вот первый вопрос:"
    )
    await send_question(message.chat.id, message.bot)


async def send_question(chat_id, bot: Bot):
    """
    Отправка следующего вопроса.
    """
    user_id = chat_id
    if user_id not in user_tests:
        user_tests[user_id] = {'current_index': 0, 'score': 0, 'errors': 0, 'questions': []}

    test_data = user_tests[user_id]

    # Если вопросы ещё не загружены, загрузить их из базы
    if not test_data['questions']:
        try:
            db_conn = await init_db()
            lang = user_state[user_id]['lang']
            category = user_state[user_id]['category']
            rows = await db_conn.fetch(
                "SELECT * FROM questions WHERE lang=$1 AND category=$2 LIMIT 30",
                lang, category
            )
            test_data['questions'] = rows
            await db_conn.close()

            if not rows:
                await bot.send_message(user_id, "Для этой категории и языка вопросы отсутствуют.")
                return
        except Exception as e:
            await bot.send_message(user_id, f"Ошибка при загрузке вопросов: {e}")
            return

    # Если все вопросы пройдены
    if test_data['current_index'] >= len(test_data['questions']):
        await show_results(user_id, bot)
        return

    # Получаем текущий вопрос
    question = test_data['questions'][test_data['current_index']]
    text = question['text']
    test_data['current_index'] += 1

    # Отправляем вопрос с клавиатурой
    await bot.send_message(user_id, f"Вопрос {test_data['current_index']}:\n{text}", reply_markup=answer_keyboard())


async def handle_answer(callback_query: types.CallbackQuery):
    """
    Обработчик ответа пользователя на вопрос.
    """
    user_id = callback_query.from_user.id
    data = callback_query.data.split("_")[1]  # Получаем выбранный вариант (A, B, C, D)

    if user_id not in user_tests:
        await callback_query.message.reply("Ваш тест не найден. Напишите /start.")
        return

    test_data = user_tests[user_id]
    current_question = test_data['questions'][test_data['current_index'] - 1]

    # Проверяем правильность ответа
    if data == current_question['correct_answer']:
        test_data['score'] += 1
        feedback = "Правильно!"
    else:
        test_data['errors'] += 1
        feedback = f"Неправильно. Правильный ответ: {current_question['correct_answer']}.\n"
        feedback += f"Пояснение: {current_question['explanation']}"

    await callback_query.answer(feedback, show_alert=True)

    # Если пользователь допустил больше одной ошибки, завершить тест
    if test_data['errors'] > 1:
        await callback_query.bot.send_message(user_id, "Вы допустили слишком много ошибок. Тест завершен.")
        del user_tests[user_id]
        return

    # Отправить следующий вопрос
    await send_question(user_id, callback_query.bot)


async def show_results(chat_id, bot: Bot):
    """
    Показывает результаты теста.
    """
    user_id = chat_id
    test_data = user_tests[user_id]

    total_questions = len(test_data['questions'])
    score = test_data['score']
    errors = test_data['errors']

    result_text = (
        f"Тест завершен!\n"
        f"Правильных ответов: {score} из {total_questions}\n"
        f"Ошибок: {errors}\n"
    )
    if errors <= 1:
        result_text += "Поздравляем, вы прошли тест!"
    else:
        result_text += "К сожалению, вы не прошли тест. Попробуйте снова!"

    await bot.send_message(user_id, result_text)
    del user_tests[user_id]


def register_handlers(dp: Dispatcher):
    """
    Регистрация обработчиков.
    """
    dp.message.register(start_handler, commands=["start"])
    dp.callback_query.register(language_choice, F.data.startswith("lang_"))
    dp.message.register(category_choice)
    dp.callback_query.register(handle_answer, F.data.startswith("answer_"))
