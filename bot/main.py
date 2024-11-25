import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

# Импортирование токена и других параметров из config.py
from config import API_TOKEN
from database import init_db, load_data_to_db
from handlers import register_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Проверяем, что токен указан
if not API_TOKEN:
    raise ValueError("API_TOKEN не указан в файле config.py. Проверьте настройки.")

# Функция для выполнения задач при старте бота
async def on_startup():
    db_conn = None
    try:
        # Инициализация базы данных
        db_conn = await init_db()
        await load_data_to_db(db_conn)
        logging.info("База данных успешно инициализирована!")
    except Exception as e:
        logging.error(f"Ошибка при инициализации базы данных: {e}")
        raise
    finally:
        if db_conn:
            await db_conn.close()  # Закрытие соединения

# Основная функция для запуска бота
async def main():
    # Инициализация бота
    bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    # Регистрация обработчиков
    register_handlers(dp)

    # Выполнение задач перед запуском бота
    await on_startup()

    # Запуск long polling
    try:
        logging.info("Бот успешно запущен!")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Произошла ошибка во время работы бота: {e}")
    finally:
        # Корректное завершение работы
        await bot.session.close()

# Запуск кода
if __name__ == "__main__":
    asyncio.run(main())
