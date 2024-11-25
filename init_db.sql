-- Создаём таблицу для хранения вопросов
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,            -- Уникальный идентификатор для вопроса
    lang TEXT NOT NULL,               -- Язык вопроса: ru, en, ge
    question_id INT NOT NULL,         -- Номер вопроса
    category TEXT NOT NULL,           -- Категория (A, B, C, ...)
    text TEXT NOT NULL,               -- Текст вопроса
    correct_answer TEXT NOT NULL,     -- Правильный ответ (A, B, C, D)
    explanation TEXT                  -- Пояснение к правильному ответу
);

-- Добавляем индексы для оптимизации запросов
CREATE INDEX idx_lang_category ON questions (lang, category);
