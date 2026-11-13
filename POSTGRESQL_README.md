# PostgreSQL

По умолчанию Meeting Processor хранит данные в файле SQLite (`meeting_processor.db`). Приложение может работать и с PostgreSQL — это нужно, когда база должна жить отдельно от контейнера приложения или обслуживаться средствами СУБД (резервные копии, репликация).

Схема и поведение приложения в обеих СУБД одинаковы. Таблицы в PostgreSQL создаются автоматически при первом запуске.

## Требования

- PostgreSQL 11 или новее.
- Драйвер `psycopg` — входит в `requirements.txt` (`pip install -r requirements.txt`).
- Пустая база данных и пользователь с правом создавать в ней таблицы.

```sql
CREATE USER meeting WITH PASSWORD '...';
CREATE DATABASE meeting_processor OWNER meeting;
```

## Подключение

Есть два равноправных способа. Если заданы оба, действует переменная окружения.

### Переменная окружения `DATABASE_URL`

```bash
DATABASE_URL=postgresql://meeting:password@db.example.com:5432/meeting_processor
```

Если переменная задана и начинается с `postgresql://` или `postgres://`, приложение работает с PostgreSQL независимо от `config.json`.

### Раздел `database` в `config.json`

```json
"database": {
  "type": "postgresql",
  "host": "db.example.com",
  "port": 5432,
  "name": "meeting_processor",
  "user": "meeting",
  "sslmode": "require"
}
```

| Поле | Значение по умолчанию | Описание |
|---|---|---|
| `type` | `sqlite` | `postgresql` включает PostgreSQL |
| `url` | — | URL подключения целиком; заменяет поля ниже |
| `host` | `localhost` | адрес сервера |
| `port` | `5432` | порт |
| `name` | `meeting_processor` | имя базы данных |
| `user` | — | пользователь |
| `password` | — | пароль; лучше задавать через `DATABASE_PASSWORD` |
| `sslmode` | — | режим TLS (`require`, `verify-full`, ...) |
| `connect_timeout` | `10` | таймаут подключения в секундах |

Пароль не обязательно хранить в `config.json`: переменная окружения `DATABASE_PASSWORD` перекрывает и поле `password`, и пароль из `url`.

Поля `path`, `backup_enabled` и `backup_interval_hours` относятся только к SQLite.

Проверить, с какой базой работает приложение, можно в `/health`: поле `database.type`.

## Перенос данных из SQLite

Скрипт `migrate_sqlite_to_postgres.py` копирует пользователей, задачи и публикации Confluence из файла SQLite в PostgreSQL.

```bash
# 1. Остановите приложение, чтобы в SQLite не появлялись новые записи.

# 2. Проверка без записи: сколько строк будет перенесено
python migrate_sqlite_to_postgres.py --sqlite meeting_processor.db \
    --postgres-url postgresql://meeting:password@db.example.com:5432/meeting_processor --dry-run

# 3. Перенос
python migrate_sqlite_to_postgres.py --sqlite meeting_processor.db \
    --postgres-url postgresql://meeting:password@db.example.com:5432/meeting_processor

# 4. Переключите приложение на PostgreSQL (DATABASE_URL или config.json) и запустите его.
```

Если `--postgres-url` не указан, параметры берутся из `DATABASE_URL` или раздела `database` в `config.json`; если не указан `--sqlite` — из `database.path`.

Что делает скрипт:

- Создаёт таблицы в PostgreSQL теми же миграциями, что и приложение.
- Переносит данные одной транзакцией: при любой ошибке PostgreSQL остаётся в прежнем состоянии.
- Сохраняет идентификаторы и даты; счётчик идентификаторов публикаций продолжается после максимального перенесённого.
- Сверяет количество строк в источнике и приёмнике.
- Файл SQLite открывает только для чтения и не изменяет — его можно оставить как резервную копию.

Параметры:

| Параметр | Описание |
|---|---|
| `--sqlite PATH` | файл SQLite |
| `--postgres-url URL` | адрес PostgreSQL |
| `--config FILE` | файл конфигурации (по умолчанию `config.json`) |
| `--dry-run` | только проверка, без записи в PostgreSQL |
| `--replace` | очистить таблицы PostgreSQL перед переносом. Без этого параметра скрипт откажется писать в непустую базу |
| `--skip-orphans` | пропустить строки, ссылающиеся на несуществующие записи (задачи без пользователя, публикации без задачи). Без этого параметра скрипт остановится и перечислит такие строки |

Файлы протоколов и транскриптов (`web_output/`, `web_uploads/`) в базе не хранятся — в ней только пути к ним. Скрипт их не трогает; каталоги должны остаться доступны приложению по тем же путям.

## Docker

В `docker-compose.yml` есть необязательный сервис `postgres`. Он запускается только с профилем `postgres`:

```bash
# .env
POSTGRES_PASSWORD=password
DATABASE_URL=postgresql://meeting:password@postgres:5432/meeting_processor

# Запуск приложения вместе с PostgreSQL
docker-compose --profile postgres up -d

# Перенос данных из meeting_processor.db (файл смонтирован в контейнер приложения)
docker-compose run --rm meeting-web python migrate_sqlite_to_postgres.py
```

Без `DATABASE_URL` приложение в контейнере продолжает работать с SQLite, как раньше. Для внешнего сервера PostgreSQL профиль не нужен — достаточно задать `DATABASE_URL`.

## Особенности

- **Время хранится в UTC**, как и в SQLite: приложение открывает соединения с часовым поясом сессии GMT.
- **Соединение открывается на каждую операцию** и закрывается после неё, пула соединений нет. При большой нагрузке поставьте перед базой PgBouncer.
- **Резервные копии** PostgreSQL делаются средствами СУБД (`pg_dump`); встроенное копирование файла относится только к SQLite.
- **Утилита `add_test_data.py`** работает только с файлом SQLite.

## Тесты

Тесты на настоящем сервере PostgreSQL выполняются, если задана переменная `TEST_DATABASE_URL`; без неё они пропускаются. Каждый тест работает в отдельной временной схеме и удаляет её.

```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres \
    python -m pytest tests/test_postgres_support.py -v
```
