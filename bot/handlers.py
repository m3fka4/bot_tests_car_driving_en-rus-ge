from aiogram import types, Dispatcher, Bot, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from keyboards import language_keyboard, category_keyboard, answer_keyboard
import logging
from database import init_db

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
            f"Вы выбрали язык: {'Русский' if lang == 'ru' else 'English' if lang == 'en' else 'ქართული'}.\n"
            "Выберите категорию прав (например, A, B, C, D):",
            reply_markup=category_keyboard()  # Отображаем клавиатуру категорий
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass  # Игнорируем, если сообщение не изменилось
        else:
            raise


async def category_choice(callback_query: types.CallbackQuery, db_conn):
    """
    Обработчик выбора категории прав.
    """
    user_id = callback_query.from_user.id
    category = callback_query.data.split("_")[1]  # Получаем категорию (A, B, C, D)

    # Проверяем, указал ли пользователь язык ранее
    if user_id not in user_state or 'lang' not in user_state[user_id]:
        await callback_query.message.reply("Сначала выберите язык. Напишите /start.")
        return

    user_state[user_id]['category'] = category
    await callback_query.message.edit_text(
        f"Вы выбрали категорию: {category}.\n"
        "Начнем тест! Вот первый вопрос:"
    )
    await send_question(callback_query.message.chat.id, callback_query.bot, db_conn)


async def send_question(chat_id, bot: Bot, db_conn):
    """
    Отправка следующего вопроса.
    """
    user_id = chat_id
    if user_id not in user_tests:
        user_tests[user_id] = {'current_index': 0, 'score': 0, 'errors': 0, 'questions': []}

    test_data = user_tests[user_id]

    if not test_data['questions']:
        try:
            lang = user_state[user_id]['lang']
            category = user_state[user_id]['category']

            logging.info(f"Загружаем вопросы для языка '{lang}' и категории '{category}'...")

            rows = await db_conn.fetch(
                """
                SELECT text, correct_answer, explanation 
                FROM questions 
                WHERE lang = $1 AND category ILIKE '%' || $2 || '%' 
                LIMIT 30
                """,
                lang, category
            )

            logging.info(f"Найдено вопросов: {len(rows)}")

            test_data['questions'] = rows

            if not rows:
                await bot.send_message(user_id, "Для этой категории и языка вопросы отсутствуют.")
                return
        except Exception as e:
            logging.error(f"Ошибка при загрузке вопросов: {e}")
            await bot.send_message(user_id, f"Ошибка при загрузке вопросов: {e}")
            return

    if test_data['current_index'] >= len(test_data['questions']):
        await show_results(user_id, bot)
        return

    question = test_data['questions'][test_data['current_index']]
    text = question['text'][:4093] + "..." if len(question['text']) > 4096 else question['text']
    test_data['current_index'] += 1

    await bot.send_message(user_id, f"Вопрос {test_data['current_index']}:\n{text}", reply_markup=answer_keyboard())

async def handle_answer(callback_query: types.CallbackQuery, db_conn):
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
    is_correct = data == current_question['correct_answer']
    if is_correct:
        test_data['score'] += 1
        feedback = "Правильно!"
    else:
        test_data['errors'] += 1
        feedback = f"Неправильно. Правильный ответ: {current_question['correct_answer']}."

    # Ответ пользователю через alert
    try:
        await callback_query.answer(feedback[:200], show_alert=True)
    except TelegramBadRequest as e:
        logging.warning(f"Ошибка отправки alert: {e}")

    # Если неправильный ответ, отправляем пояснение как отдельное сообщение
    if not is_correct and current_question.get('explanation'):
        explanation = current_question['explanation']
        if len(explanation) > 4096:  # Ограничиваем длину текстового сообщения
            explanation = explanation[:4093] + "..."
        await callback_query.message.reply(f"Пояснение: {explanation}")

    # Завершаем тест, если ошибок больше 1
    if test_data['errors'] > 1:
        await callback_query.message.answer("Вы допустили слишком много ошибок. Тест завершен.")
        del user_tests[user_id]
        return

    # Отправить следующий вопрос
    await send_question(user_id, callback_query.bot, db_conn)



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

def register_handlers(dp: Dispatcher, db_conn):
    """
    Регистрация обработчиков.
    """
    dp.message.register(start_handler, CommandStart())
    dp.callback_query.register(language_choice, F.data.startswith("lang_"))

    # Обертка для передачи db_conn в category_choice
    async def category_choice_handler(callback_query: types.CallbackQuery):
        await category_choice(callback_query, db_conn)

    dp.callback_query.register(category_choice_handler, F.data.startswith("category_"))

    # Обертка для передачи db_conn в handle_answer
    async def handle_answer_handler(callback_query: types.CallbackQuery):
        await handle_answer(callback_query, db_conn)

    dp.callback_query.register(handle_answer_handler, F.data.startswith("answer_"))
