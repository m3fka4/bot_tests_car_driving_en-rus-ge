import asyncpg
import pandas as pd

# Асинхронная функция для загрузки данных из Excel в базу данных
async def load_data_to_db(db_conn):
    """
    Загружает данные из Excel в таблицу 'questions' базы данных.
    """
    # Загрузка данных из листов Excel
    df_ru = pd.read_excel("data/Exam_Data.xlsx", sheet_name="ru")
    df_en = pd.read_excel("data/Exam_Data.xlsx", sheet_name="en")
    df_ge = pd.read_excel("data/Exam_Data.xlsx", sheet_name="ge")

    # Асинхронная транзакция для вставки данных
    async with db_conn.transaction():
        for lang, df in [("ru", df_ru), ("en", df_en), ("ge", df_ge)]:
            for _, row in df.iterrows():
                await db_conn.execute(
                    """
                    INSERT INTO questions (lang, question_id, category, text, correct_answer, explanation)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (question_id) DO NOTHING
                    """,
                    lang,
                    row['Номер вопроса'],
                    row['Категория'],
                    row['Текст вопроса'],
                    row['Правильный ответ'],
                    row['Пояснение']
                )

# Асинхронная функция для инициализации базы данных
async def init_db():
    """
    Создаёт подключение к базе данных и создаёт таблицу 'questions', если её нет.
    """
    # Подключение к базе данных
    db_conn = await asyncpg.connect(
        user="postgres",
        password="password",
        database="exam_bot",
        host="db",
        port=5432
    )

    # Создание таблицы вопросов, если её нет
    await db_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            lang TEXT NOT NULL,
            question_id SERIAL PRIMARY KEY,
            category TEXT NOT NULL,
            text TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT
        );
        """
    )
    return db_conn
