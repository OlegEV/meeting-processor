# Система аутентификации и авторизации

Веб-приложение для обработки встреч теперь поддерживает многопользовательский режим с внешней аутентификацией через IdP провайдер.

## Основные возможности

- ✅ **Аутентификация через внешний IdP** - получение identity token в заголовке `X-Identity-Token`
- ✅ **Изоляция пользовательских данных** - каждый пользователь видит только свои задачи
- ✅ **База данных SQLite** - персистентное хранение пользователей и задач
- ✅ **Пользовательские директории** - файлы организованы по пользователям
- ✅ **Автоматическое создание пользователей** - при первом входе
- ✅ **Полная обратная совместимость** - все существующие функции сохранены

## Архитектура

```
[Reverse Proxy/Auth Server] 
    ↓ (Cookie → JWT Token)
[Web Application + Auth Middleware]
    ↓ (User Context)
[Database Layer (SQLite)]
    ↓ (User-filtered Data)
[File System (User Directories)]
```

## Конфигурация

### config.json

```json
{
  "auth": {
    "token_header": "X-Identity-Token",
    "jwt_algorithm": "RS256",
    "token_validation": {
      "verify_signature": false,
      "verify_exp": true,
      "verify_aud": false
    }
  },
  "database": {
    "type": "sqlite",
    "path": "meeting_processor.db",
    "backup_enabled": true,
    "backup_interval_hours": 24
  },
  "user_files": {
    "base_path": "web_output",
    "structure": "user_based"
  }
}
```

### Переменные окружения

```bash
# Для Docker
AUTH_TOKEN_HEADER=X-Identity-Token
```

## Структура файлов

```
meeting-processor/
├── auth/                          # Модуль аутентификации
│   ├── __init__.py
│   ├── jwt_utils.py              # Утилиты для работы с JWT
│   ├── token_validator.py        # Валидация токенов
│   ├── user_context.py           # Контекст пользователя
│   ├── decorators.py             # Декораторы защиты маршрутов
│   └── user_manager.py           # Менеджер пользователей
├── database/                      # Модуль базы данных
│   ├── __init__.py
│   ├── models.py                 # Модели данных
│   ├── db_manager.py             # Менеджер базы данных
│   └── migrations/               # Миграции
│       ├── 001_initial_schema.sql
│       └── 002_add_indexes.sql
├── web_uploads/                   # Загруженные файлы
│   ├── user_123/                 # Файлы пользователя 123
│   └── user_456/                 # Файлы пользователя 456
├── web_output/                    # Результаты обработки
│   ├── user_123/                 # Результаты пользователя 123
│   │   ├── job_abc/
│   │   │   ├── transcript.txt
│   │   │   └── summary.md
│   │   └── job_def/
│   └── user_456/                 # Результаты пользователя 456
├── meeting_processor.db          # База данных SQLite
├── config.json                   # Конфигурация (обновлена)
├── requirements.txt              # Зависимости (добавлен PyJWT)
└── test_auth.py                  # Скрипт тестирования
```

## База данных

### Таблица users

| Поле | Тип | Описание |
|------|-----|----------|
| user_id | TEXT (PK) | Идентификатор из JWT claim 'sub' |
| email | TEXT | Email пользователя |
| name | TEXT | Имя пользователя |
| created_at | TIMESTAMP | Дата создания |
| last_login | TIMESTAMP | Последний вход |

### Таблица jobs

| Поле | Тип | Описание |
|------|-----|----------|
| job_id | TEXT (PK) | Уникальный ID задачи |
| user_id | TEXT (FK) | Владелец задачи |
| filename | TEXT | Имя файла |
| template | TEXT | Тип шаблона |
| status | TEXT | Статус (uploaded/processing/completed/error) |
| progress | INTEGER | Прогресс (0-100) |
| file_path | TEXT | Путь к исходному файлу |
| transcript_file | TEXT | Путь к транскрипту |
| summary_file | TEXT | Путь к протоколу |
| created_at | TIMESTAMP | Дата создания |
| completed_at | TIMESTAMP | Дата завершения |

## Использование

### Запуск приложения

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск веб-приложения
python run_web.py

# Или с Docker
docker-compose up meeting-web
```

### Тестирование аутентификации

```bash
# Запуск тестов
python test_auth.py

# Только получение тестовых токенов
python test_auth.py --tokens-only

# Тестирование на другом URL
python test_auth.py --url http://localhost:8001
```

### Формат JWT токена

Приложение ожидает JWT токен в заголовке `X-Identity-Token` со следующими claims:

```json
{
  "sub": "user_123",                    // Обязательно: ID пользователя
  "email": "user@company.com",          // Опционально: Email
  "name": "John Doe",                   // Опционально: Имя
  "iat": 1640995200,                    // Время создания
  "exp": 1641081600                     // Срок действия
}
```

### Примеры запросов

```bash
# Получение главной страницы
curl -H "X-Identity-Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0..." \
     http://localhost:5000/

# Получение списка задач пользователя
curl -H "X-Identity-Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0..." \
     http://localhost:5000/jobs

# Получение статуса задачи
curl -H "X-Identity-Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0..." \
     http://localhost:5000/api/status/job_123
```

## API Endpoints

Все endpoints теперь требуют аутентификации (кроме `/health`):

| Endpoint | Метод | Описание | Аутентификация |
|----------|-------|----------|----------------|
| `/health` | GET | Health check | ❌ Не требуется |
| `/` | GET | Главная страница | ✅ Требуется |
| `/upload` | POST | Загрузка файла | ✅ Требуется |
| `/status/<job_id>` | GET | Статус задачи | ✅ Требуется |
| `/api/status/<job_id>` | GET | API статуса | ✅ Требуется |
| `/download/<job_id>/<type>` | GET | Скачивание файла | ✅ Требуется |
| `/view/<job_id>/<type>` | GET | Просмотр файла | ✅ Требуется |
| `/jobs` | GET | Список задач | ✅ Требуется |

## Безопасность

### Изоляция данных

- Каждый пользователь видит только свои задачи
- Файлы хранятся в пользовательских директориях
- Все запросы к БД фильтруются по `user_id`
- Проверка доступа к файлам перед отдачей

### Валидация токенов

- Проверка формата JWT
- Проверка срока действия (если включено)
- Извлечение `user_id` из claim `sub`
- Логирование попыток доступа

### Конфигурация безопасности

```json
{
  "auth": {
    "token_validation": {
      "verify_signature": false,    // Доверяем reverse proxy
      "verify_exp": true,          // Проверяем срок действия
      "verify_aud": false          // Не проверяем аудиторию
    }
  }
}
```

## Мониторинг

### Health Check

```bash
curl http://localhost:5000/health
```

Ответ:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-17T11:00:00Z",
  "version": "1.0.0",
  "database": {
    "users_count": 5,
    "jobs_count": 23,
    "db_size_mb": 1.2
  },
  "auth": {
    "enabled": true,
    "token_header": "X-Identity-Token"
  }
}
```

### Логирование

Логи аутентификации записываются в `logs/web_app.log`:

```
2025-06-17 11:00:00 - auth.token_validator - INFO - Токен валиден для пользователя: user_123
2025-06-17 11:00:01 - auth.user_manager - INFO - Создан новый пользователь: user_456
2025-06-17 11:00:02 - run_web - INFO - Задача abc123 создана для пользователя user_123
```

## Миграция существующих данных

При первом запуске с новой системой:

1. Создается база данных SQLite
2. Существующие задачи в памяти теряются (это нормально)
3. Новые задачи сохраняются в БД с привязкой к пользователям
4. Файлы организуются в пользовательские директории

## Troubleshooting

### Ошибка "Authentication required"

- Проверьте наличие заголовка `X-Identity-Token`
- Убедитесь, что токен не истек
- Проверьте формат JWT токена

### Ошибка "Job not found or access denied"

- Задача принадлежит другому пользователю
- Задача была удалена
- Неверный `job_id`

### Ошибка базы данных

- Проверьте права доступа к файлу `meeting_processor.db`
- Убедитесь, что директория доступна для записи
- Проверьте логи в `logs/web_app.log`

### Проблемы с файлами

- Проверьте структуру директорий `web_output/user_id/`
- Убедитесь в правах доступа к файлам
- Проверьте настройку `user_files.structure` в конфигурации

## Разработка

### Добавление новых endpoints

```python
from auth import require_auth, get_current_user_id

@app.route('/my-endpoint')
@require_auth()
def my_endpoint():
    user_id = get_current_user_id()
    # Ваш код с учетом пользователя
    return jsonify({'user_id': user_id})
```

### Работа с базой данных

```python
# Получение задач пользователя
user_jobs = db_manager.get_user_jobs(user_id)

# Создание задачи
job_data = {'job_id': 'abc', 'user_id': user_id, ...}
db_manager.create_job(job_data)

# Обновление задачи с проверкой доступа
db_manager.update_job(job_id, update_data, user_id)
```

### Тестирование

```python
# Создание тестового токена
from test_auth import create_test_jwt

token = create_test_jwt('test_user', 'test@example.com', 'Test User')
headers = {'X-Identity-Token': token}

# Использование в тестах
response = client.get('/jobs', headers=headers)
```

## Поддержка

При возникновении проблем:

1. Проверьте логи в `logs/web_app.log`
2. Запустите `python test_auth.py` для диагностики
3. Проверьте конфигурацию в `config.json`
4. Убедитесь в корректности JWT токенов