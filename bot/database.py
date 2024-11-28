import os
import asyncpg
import pandas as pd
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Получение параметров подключения к базе данных из переменных окружения
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "exam_bot")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))


async def create_database_if_not_exists():
    """
    Создает базу данных, если она отсутствует.
    """
    try:
        # Подключаемся к системной базе данных "postgres"
        sys_conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres",  # Подключение к системной базе
            host=DB_HOST,
            port=DB_PORT
        )

        # Проверяем, существует ли база данных
        result = await sys_conn.fetchrow(
            "SELECT 1 FROM pg_database WHERE datname = $1", DB_NAME
        )
        if not result:
            logging.info(f"Создаем базу данных '{DB_NAME}'...")
            await sys_conn.execute(f"CREATE DATABASE {DB_NAME}")
        else:
            logging.info(f"База данных '{DB_NAME}' уже существует.")
        await sys_conn.close()
    except Exception as e:
        logging.error(f"Ошибка при проверке или создании базы данных: {e}")
        raise


async def load_data_to_db(db_conn):
    """
    Загружает данные из Excel в таблицу 'questions' базы данных.
    Загружает данные только если таблица 'questions' пуста.
    """
    try:
        # Проверяем, есть ли записи в таблице
        existing_data = await db_conn.fetchrow("SELECT COUNT(*) FROM questions")
        if existing_data and existing_data["count"] > 0:
            logging.info("Таблица 'questions' уже содержит данные. Загрузка пропущена.")
            return

        # Указываем путь к файлу
        file_path = os.path.join(os.path.dirname(__file__), "data", "Exam Data.xlsx")
        logging.info(f"Загрузка данных из файла {file_path}...")

        # Проверяем наличие файла
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл '{file_path}' не найден.")

        # Листы и необходимые колонки
        sheets = ["ru", "en", "ge"]
        required_columns = ['Номер вопроса', 'Категория', 'Текст вопроса', 'Правильный ответ']

        data_frames = []

        # Загружаем данные из Excel по листам
        for sheet in sheets:
            try:
                logging.info(f"Чтение данных с листа '{sheet}'...")
                df = pd.read_excel(file_path, sheet_name=sheet)
                if not all(col in df.columns for col in required_columns):
                    raise ValueError(f"В листе '{sheet}' отсутствуют необходимые колонки: {required_columns}")
                df['lang'] = sheet  # Добавляем колонку с языком
                data_frames.append(df)
            except Exception as e:
                logging.error(f"Ошибка при чтении листа '{sheet}': {e}")
                raise

        # Объединяем данные из всех листов
        df_combined = pd.concat(data_frames, ignore_index=True)

        # Убираем строки с пустыми значениями в обязательных колонках
        df_combined = df_combined.dropna(subset=required_columns)

        # Приведение данных к строковому формату
        for column in ['Категория', 'Текст вопроса', 'Правильный ответ', 'Пояснение']:
            df_combined[column] = df_combined[column].fillna("").astype(str)

        # Преобразование номера вопроса
        def clean_question_number(value):
            """
            Преобразует значение из колонки 'Номер вопроса' в целое число, удаляя лишние символы.
            """
            try:
                return int(str(value).replace('#', '').strip())
            except ValueError:
                logging.warning(f"Некорректное значение номера вопроса: {value}. Пропускаем.")
                return None

        df_combined['Номер вопроса'] = df_combined['Номер вопроса'].apply(clean_question_number)
        df_combined = df_combined.dropna(subset=['Номер вопроса'])  # Убираем строки с некорректными номерами вопросов

        # Вставляем данные в базу данных
        async with db_conn.transaction():
            for _, row in df_combined.iterrows():
                try:
                    await db_conn.execute(
                        """
                        INSERT INTO questions (lang, question_id, category, text, correct_answer, explanation)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (question_id) DO NOTHING
                        """,
                        row['lang'],  # Язык
                        int(row['Номер вопроса']),  # Номер вопроса
                        row['Категория'].strip(),  # Категория
                        row['Текст вопроса'].strip(),  # Текст вопроса
                        row['Правильный ответ'].strip(),  # Правильный ответ
                        row.get('Пояснение', "").strip()  # Пояснение
                    )
                except Exception as e:
                    logging.error(f"Ошибка при вставке строки: {row}. Ошибка: {e}")

        logging.info("Данные успешно загружены в базу данных.")

    except FileNotFoundError as e:
        logging.error(f"Файл Excel не найден: {e}")
        raise
    except Exception as e:
        logging.error(f"Ошибка при загрузке данных в базу: {e}")
        raise


async def init_db():
    """
    Создаёт подключение к базе данных и создаёт таблицу 'questions', если её нет.
    """
    try:
        # Проверяем наличие базы данных и создаем её при необходимости
        await create_database_if_not_exists()

        # Подключение к базе данных
        db_conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT
        )

        # Создание таблицы вопросов, если её нет
        await db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                lang TEXT NOT NULL,
                question_id INT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                text TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation TEXT
            );
            """
        )
        logging.info("Таблица 'questions' успешно создана или уже существует.")

        # Загрузка данных в таблицу только если она пуста
        await load_data_to_db(db_conn)

        return db_conn
    except Exception as e:
        logging.error(f"Ошибка при инициализации базы данных: {e}")
        raise
