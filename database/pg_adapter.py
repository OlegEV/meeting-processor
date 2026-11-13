#!/usr/bin/env python3
"""
Адаптер PostgreSQL для DatabaseManager.

Соединение и курсор повторяют интерфейс sqlite3, которым пользуется приложение
(``with conn:``, ``conn.cursor()``, ``cursor.execute(sql, params)`` с плейсхолдерами ``?``,
строки с доступом по индексу и по имени колонки, ``dict(row)``), поэтому SQL-код
DatabaseManager и run_web.py работает с обеими СУБД без изменений.

Отличия от sqlite3, о которых нужно помнить:
- ``with conn:`` по выходу из блока не только фиксирует транзакцию, но и закрывает соединение;
- ``cursor.lastrowid`` недоступен — используйте ``INSERT ... RETURNING id``;
- значения TIMESTAMP/DATE возвращаются строками (как в SQLite), NUMERIC — числами float.
"""

import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

# psycopg — опциональная зависимость: приложение с SQLite работает и без неё
try:
    import psycopg
    from psycopg.adapt import Loader
    from psycopg.conninfo import make_conninfo
    from psycopg.types.numeric import FloatLoader
    PSYCOPG_AVAILABLE = True
    PSYCOPG_IMPORT_ERROR = None
except ImportError as import_error:  # pragma: no cover - зависит от окружения
    psycopg = None
    Loader = object
    PSYCOPG_AVAILABLE = False
    PSYCOPG_IMPORT_ERROR = import_error

# Переменные окружения, перекрывающие настройки подключения из config.json
DATABASE_URL_ENV_VAR = "DATABASE_URL"
DATABASE_PASSWORD_ENV_VAR = "DATABASE_PASSWORD"

# Параметры сессии: время в UTC (как CURRENT_TIMESTAMP в SQLite) и даты в формате ISO.
# Пояс задан как GMT: это имя встроено в PostgreSQL и работает даже на сервере без базы
# часовых поясов, где "UTC" отклоняется.
SESSION_OPTIONS = "-c timezone=GMT -c datestyle=ISO,YMD"

POSTGRES_TYPE_ALIASES = ("postgresql", "postgres", "pg", "psql")
POSTGRES_URL_PREFIXES = ("postgresql://", "postgres://")


def is_postgres_url(value: Optional[str]) -> bool:
    """Проверяет, что строка — URL подключения к PostgreSQL"""
    return bool(value) and value.strip().lower().startswith(POSTGRES_URL_PREFIXES)


def resolve_database_type(config: Dict[str, Any]) -> str:
    """
    Определяет тип СУБД: 'sqlite' или 'postgresql'.

    Приоритет: DATABASE_URL с адресом PostgreSQL > database.type из конфигурации > sqlite.
    """
    if is_postgres_url(os.getenv(DATABASE_URL_ENV_VAR)):
        return "postgresql"

    db_type = str(config.get("type") or "sqlite").strip().lower()
    if db_type in POSTGRES_TYPE_ALIASES:
        return "postgresql"
    return "sqlite"


def build_conninfo(config: Dict[str, Any]) -> str:
    """
    Собирает строку подключения к PostgreSQL.

    Источники в порядке приоритета:
    1. переменная окружения DATABASE_URL;
    2. database.url из конфигурации;
    3. отдельные поля database.host / port / name / user / password / sslmode.

    Пароль из DATABASE_PASSWORD перекрывает пароль из конфигурации — так его не нужно
    хранить в config.json.
    """
    if not PSYCOPG_AVAILABLE:
        raise RuntimeError(_missing_driver_message())

    params: Dict[str, Any] = {}

    env_password = os.getenv(DATABASE_PASSWORD_ENV_VAR)
    connect_timeout = config.get("connect_timeout", 10)
    if connect_timeout:
        params["connect_timeout"] = int(connect_timeout)

    env_url = os.getenv(DATABASE_URL_ENV_VAR)
    url = env_url.strip() if is_postgres_url(env_url) else (config.get("url") or "").strip()

    if url:
        if env_password:
            params["password"] = env_password
        return make_conninfo(url, **params)

    params["host"] = config.get("host", "localhost")
    params["port"] = int(config.get("port", 5432))
    params["dbname"] = config.get("name") or config.get("dbname") or config.get("database") or "meeting_processor"

    user = config.get("user") or config.get("username")
    if user:
        params["user"] = user

    password = env_password or config.get("password")
    if password:
        params["password"] = password

    sslmode = config.get("sslmode")
    if sslmode:
        params["sslmode"] = sslmode

    return make_conninfo(**params)


def describe_conninfo(conninfo: str) -> str:
    """Возвращает описание подключения без пароля — для логов и /health"""
    if not PSYCOPG_AVAILABLE:
        return "postgresql"
    try:
        from psycopg.conninfo import conninfo_to_dict
        params = conninfo_to_dict(conninfo)
    except Exception:
        return "postgresql"

    host = params.get("host") or "localhost"
    port = params.get("port") or 5432
    dbname = params.get("dbname") or ""
    user = params.get("user")
    prefix = f"{user}@" if user else ""
    return f"postgresql://{prefix}{host}:{port}/{dbname}"


def translate_placeholders(sql: str) -> str:
    """
    Переводит плейсхолдеры SQLite (``?``) в плейсхолдеры psycopg (``%s``).

    Символы внутри строковых литералов и идентификаторов в кавычках не трогаются,
    а ``%`` экранируется как ``%%`` — иначе psycopg примет его за плейсхолдер.
    """
    result: List[str] = []
    quote: Optional[str] = None

    for char in sql:
        if quote:
            # Внутри литерала: '' и "" — экранированные кавычки, состояние переключается дважды
            if char == quote:
                quote = None
            result.append("%%" if char == "%" else char)
        elif char in ("'", '"'):
            quote = char
            result.append(char)
        elif char == "?":
            result.append("%s")
        elif char == "%":
            result.append("%%")
        else:
            result.append(char)

    return "".join(result)


class PgRow(tuple):
    """Строка результата: доступ по индексу, по имени колонки и преобразование в dict"""

    __slots__ = ()
    _columns: Sequence[str] = ()

    def keys(self) -> List[str]:
        return list(self._columns)

    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                return tuple.__getitem__(self, self._columns.index(key))
            except ValueError:
                raise IndexError(f"No item with that key: {key}") from None
        return tuple.__getitem__(self, key)


def _pg_row_factory(cursor):
    """Фабрика строк psycopg, создающая PgRow с именами колонок текущего запроса"""
    description = cursor.description
    if description is None:
        # Запрос не возвращает строк (INSERT/UPDATE/DDL)
        def no_result(values):  # pragma: no cover - psycopg не вызывает фабрику без результата
            raise psycopg.ProgrammingError("the last operation didn't produce a result")
        return no_result

    columns = tuple(column.name for column in description)
    row_class = type("PgRow", (PgRow,), {"__slots__": (), "_columns": columns})
    return row_class


class _TextLoader(Loader):
    """Возвращает значение PostgreSQL как строку — так TIMESTAMP и DATE отдаёт SQLite"""

    def load(self, data):
        return bytes(data).decode("utf-8")


class PgCursor:
    """Курсор с интерфейсом sqlite3.Cursor поверх курсора psycopg"""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql: str, params: Iterable[Any] = ()):
        params = tuple(params) if params is not None else ()
        if params:
            self._cursor.execute(translate_placeholders(sql), params)
        else:
            # Без параметров psycopg не разбирает плейсхолдеры, и '%' экранировать не нужно
            self._cursor.execute(sql)
        return self

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]):
        self._cursor.executemany(translate_placeholders(sql), [tuple(p) for p in seq_of_params])
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size: Optional[int] = None):
        return self._cursor.fetchmany(size) if size else self._cursor.fetchmany()

    def __iter__(self):
        return iter(self._cursor)

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    @property
    def lastrowid(self):
        raise AttributeError(
            "lastrowid не поддерживается в PostgreSQL — используйте INSERT ... RETURNING id"
        )

    def close(self):
        self._cursor.close()


class PgConnection:
    """Соединение с интерфейсом sqlite3.Connection поверх соединения psycopg"""

    def __init__(self, connection):
        self._connection = connection

    def cursor(self) -> PgCursor:
        return PgCursor(self._connection.cursor())

    def execute(self, sql: str, params: Iterable[Any] = ()) -> PgCursor:
        return self.cursor().execute(sql, params)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        if not self._connection.closed:
            self._connection.close()

    @property
    def closed(self) -> bool:
        return self._connection.closed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # sqlite3 в этом месте только фиксирует транзакцию, а соединение закрывает сборщик мусора.
        # Серверное соединение PostgreSQL так оставлять нельзя — закрываем его явно.
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def connect(conninfo: str) -> PgConnection:
    """
    Открывает соединение с PostgreSQL.

    Часовой пояс сессии — UTC: CURRENT_TIMESTAMP в SQLite тоже возвращает время в UTC,
    и приложение на это рассчитывает.
    """
    if not PSYCOPG_AVAILABLE:
        raise RuntimeError(_missing_driver_message())

    # Свои параметры сессии добавляем к заданным в строке подключения
    # (например, options=-csearch_path=... для работы в отдельной схеме)
    from psycopg.conninfo import conninfo_to_dict
    user_options = conninfo_to_dict(conninfo).get("options") or ""
    options = f"{user_options} {SESSION_OPTIONS}".strip()

    connection = psycopg.connect(conninfo, row_factory=_pg_row_factory, options=options)

    # Значения дат возвращаем строками, как SQLite, а NUMERIC (AVG и т.п.) — как float
    for type_name in ("timestamp", "timestamptz", "date"):
        connection.adapters.register_loader(type_name, _TextLoader)
    connection.adapters.register_loader("numeric", FloatLoader)

    return PgConnection(connection)


def _missing_driver_message() -> str:
    return (
        "Для работы с PostgreSQL установите драйвер: pip install \"psycopg[binary]\" "
        f"(ошибка импорта: {PSYCOPG_IMPORT_ERROR})"
    )
