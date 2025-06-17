-- Миграция 001: Создание начальной схемы базы данных
-- Дата: 2025-06-17
-- Описание: Создание таблиц users и jobs для системы обработки встреч

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT,
    full_name TEXT,
    given_name TEXT,
    family_name TEXT,
    preferred_username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Таблица задач обработки
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    template TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded',
    progress INTEGER DEFAULT 0,
    message TEXT DEFAULT '',
    file_path TEXT,
    transcript_file TEXT,
    summary_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    original_job_id TEXT,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);