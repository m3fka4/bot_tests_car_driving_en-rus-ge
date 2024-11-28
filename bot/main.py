import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import API_TOKEN
from handlers import register_handlers
from database import init_db  # Импортируем функцию для подключения к БД

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def main():
    """
    Основная функция для запуска бота.
    """
    if not API_TOKEN:
        raise ValueError("API_TOKEN не указан в config.py")

    # Создаем сессию для бота
    session = AiohttpSession()
    bot = Bot(
        token=API_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Инициализация подключения к базе данных
    db_conn = await init_db()

    # Регистрируем обработчики, передавая db_conn
    register_handlers(dp, db_conn)

    try:
        logging.info("Бот запущен...")
        await dp.start_polling(bot)
    finally:
        # Закрываем сессию бота и подключение к базе данных
        await bot.session.close()
        await db_conn.close()

if __name__ == "__main__":
    asyncio.run(main())
