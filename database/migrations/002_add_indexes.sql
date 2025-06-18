-- Миграция 002: Добавление индексов для производительности
-- Дата: 2025-06-17
-- Описание: Создание индексов для оптимизации запросов

-- Индексы для таблицы jobs
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs (user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON jobs (user_id, status);

-- Индексы для таблицы users
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users (last_login);