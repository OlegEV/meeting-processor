# Быстрое руководство по запуску тестов

Для запуска нужен только `pytest` (для отчёта о покрытии — ещё `pytest-cov`). Сеть, Deepgram, Claude и Confluence в тестах не используются.

## Запуск

```bash
# Все тесты
python -m pytest tests -q

# То же через test runner
python run_tests.py

# Только unit-тесты
python run_tests.py quick

# Отдельные категории: unit, integration, security, performance, e2e
python run_tests.py --categories integration e2e --verbose

# Все тесты с покрытием (нужен pytest-cov)
python run_tests.py full
```

## Состав тестов

| Категория | Файл | Что проверяет |
|---|---|---|
| unit | `tests/test_database_models.py` | модели, схема и валидаторы базы данных |
| unit | `tests/test_confluence_client.py` | клиент Confluence, конвертация markdown, сервис публикации |
| unit | `tests/test_confluence_encryption.py` | шифрование и хранение токенов Confluence |
| unit | `tests/test_protocol_generator.py` | список участников в промпте протокола |
| unit | `tests/test_admin_role.py` | определение администратора |
| unit | `tests/test_space_key_auto_extraction.py` | извлечение `space_key` и `page_id` из URL Confluence |
| integration | `tests/test_database_integration.py` | операции `DatabaseManager`, каскады, миграции |
| integration | `tests/test_flask_integration.py` | маршруты Flask, аутентификация |
| security | `tests/test_security.py` | шифрование токенов, изоляция пользователей, SQL-инъекции, XSS, обход путей |
| performance | `tests/test_performance.py` | время массовых операций с базой |
| e2e | `tests/test_end_to_end.py` | сквозные сценарии: загрузка → протокол → публикация в Confluence |

`tests/test_fixtures.py` — фабрики тестовых данных, тестов не содержит.

## Как устроена аутентификация в тестах

- `tests/test_flask_integration.py` работает в отладочном режиме: в тестовом конфиге `auth.debug_mode: true`, а `auth.debug_user` совпадает с тестовым пользователем.
- `tests/test_security.py` и `tests/test_end_to_end.py` работают с выключенным отладочным режимом; нужный пользователь задаётся подменой `token_validator.validate_request`.
- Переменная `AUTH_DEBUG_MODE` из локального `.env` перекрывает конфиг, поэтому тесты фиксируют её на время создания приложения.

## Отладка

```bash
# Один тест
python -m pytest tests/test_database_models.py::TestUser::test_user_creation -v -s

# Остановиться на первой ошибке
python -m pytest tests/test_confluence_client.py -x -v

# Подробный вывод
python -m pytest tests/test_flask_integration.py -v -s --tb=long
```

## Особенности Windows

Соединения `sqlite3` закрываются только при сборке мусора, а Windows не даёт удалить открытый файл базы. Поэтому в `tearDown` тесты обнуляют ссылки на приложение и вызывают `gc.collect()` перед удалением временных файлов.
