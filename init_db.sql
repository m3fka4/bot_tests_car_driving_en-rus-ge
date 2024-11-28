-- Создаём базу данных, если она отсутствует
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_database WHERE datname = 'exam_bot'
    ) THEN
        RAISE NOTICE 'Создаем базу данных: exam_bot';
        PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE exam_bot');
    ELSE
        RAISE NOTICE 'База данных "exam_bot" уже существует.';
    END IF;
END
$$ LANGUAGE plpgsql;

-- Подключаемся к базе данных
\c exam_bot;

-- Создаём таблицу для хранения вопросов, если её нет
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,            -- Уникальный идентификатор для вопроса
    lang TEXT NOT NULL,               -- Язык вопроса: ru, en, ge
    question_id INT UNIQUE NOT NULL,  -- Номер вопроса (уникальный)
    category TEXT NOT NULL,           -- Категория (A, B, C, ...)
    text TEXT NOT NULL,               -- Текст вопроса
    correct_answer TEXT NOT NULL,     -- Правильный ответ (A, B, C, D)
    explanation TEXT                  -- Пояснение к правильному ответу
);

-- Добавляем индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_lang_category ON questions (lang, category);
CREATE INDEX IF NOT EXISTS idx_question_id ON questions (question_id);

-- Вывод успешного завершения
DO $$
BEGIN
    RAISE NOTICE 'Таблица "questions" и индексы успешно созданы или уже существуют.';
END
$$ LANGUAGE plpgsql;
