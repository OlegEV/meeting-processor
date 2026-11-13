#!/usr/bin/env python3
"""
Перенос данных Meeting Processor из SQLite в PostgreSQL.

Скрипт создаёт схему в PostgreSQL (те же миграции, что выполняет приложение), копирует
таблицы users, jobs и confluence_publications с сохранением идентификаторов и сверяет
количество строк. Файл SQLite открывается только для чтения и не изменяется.

Примеры:
    # Параметры PostgreSQL берутся из config.json (раздел database) и переменных окружения
    python migrate_sqlite_to_postgres.py

    # Явное указание источника и приёмника
    python migrate_sqlite_to_postgres.py --sqlite meeting_processor.db \\
        --postgres-url postgresql://meeting:secret@localhost:5432/meeting_processor

    # Проверка без записи в PostgreSQL
    python migrate_sqlite_to_postgres.py --dry-run
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Загружаем переменные окружения из .env (DATABASE_URL, DATABASE_PASSWORD)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database import pg_adapter
from database.db_manager import DatabaseManager

# Таблицы в порядке, в котором соблюдаются внешние ключи
TABLES: Tuple[str, ...] = ('users', 'jobs', 'confluence_publications')

# Колонки с датами: пустые строки SQLite переносятся как NULL
TIMESTAMP_COLUMNS = {
    'users': ('created_at', 'last_login'),
    'jobs': ('created_at', 'completed_at'),
    'confluence_publications': ('created_at', 'updated_at', 'last_retry_at'),
}

BATCH_SIZE = 500


class MigrationError(Exception):
    """Ошибка переноса данных с понятным пользователю описанием"""


def open_sqlite_readonly(path: str) -> sqlite3.Connection:
    """Открывает файл SQLite только для чтения"""
    db_file = Path(path)
    if not db_file.is_file():
        raise MigrationError(f"Файл SQLite не найден: {path}")

    connection = sqlite3.connect(f"{db_file.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def sqlite_tables(connection: sqlite3.Connection) -> List[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return [row[0] for row in rows]


def table_columns(connection, table: str, is_postgres: bool) -> List[str]:
    """Возвращает список колонок таблицы"""
    cursor = connection.cursor()
    if is_postgres:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = ? ORDER BY ordinal_position",
            (table,)
        )
        return [row[0] for row in cursor.fetchall()]

    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def postgres_column_types(pg_conn, table: str) -> Dict[str, str]:
    """Возвращает типы колонок таблицы PostgreSQL: {'progress': 'integer', ...}"""
    cursor = pg_conn.cursor()
    cursor.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = ?",
        (table,)
    )
    return {row[0]: row[1] for row in cursor.fetchall()}


def count_rows(connection, table: str) -> int:
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0]


def postgres_row_counts(pg_conn) -> Dict[str, int]:
    """Считает строки в таблицах PostgreSQL; несозданная таблица считается пустой"""
    counts: Dict[str, int] = {}
    cursor = pg_conn.cursor()
    for table in TABLES:
        cursor.execute("SELECT to_regclass(?)", (table,))
        exists = cursor.fetchone()[0] is not None
        counts[table] = count_rows(pg_conn, table) if exists else 0
    return counts


def find_orphans(sqlite_conn: sqlite3.Connection, tables: Sequence[str]) -> Dict[str, List[str]]:
    """Ищет строки, нарушающие внешние ключи: в PostgreSQL они не вставятся"""
    orphans: Dict[str, List[str]] = {}

    if 'jobs' in tables and 'users' in tables:
        rows = sqlite_conn.execute(
            "SELECT j.job_id FROM jobs j LEFT JOIN users u ON j.user_id = u.user_id "
            "WHERE u.user_id IS NULL"
        ).fetchall()
        if rows:
            orphans['jobs'] = [row[0] for row in rows]

    if 'confluence_publications' in tables and 'jobs' in tables:
        rows = sqlite_conn.execute(
            "SELECT p.id FROM confluence_publications p LEFT JOIN jobs j ON p.job_id = j.job_id "
            "WHERE j.job_id IS NULL"
        ).fetchall()
        if rows:
            orphans['confluence_publications'] = [str(row[0]) for row in rows]

    return orphans


def normalize_value(table: str, column: str, value: Any, pg_type: str = 'text') -> Any:
    """
    Приводит значение SQLite к виду, который примет PostgreSQL.

    SQLite не следит за типами колонок, поэтому значение приводится к типу колонки приёмника.
    """
    if value is None:
        return None

    if column in TIMESTAMP_COLUMNS.get(table, ()):
        # Пустая строка вместо даты переносится как NULL
        text = str(value).strip()
        return text or None

    if pg_type in ('integer', 'bigint', 'smallint'):
        if isinstance(value, str) and not value.strip():
            return None
        return int(float(value))

    if pg_type == 'text':
        if isinstance(value, bytes):
            value = value.decode('utf-8', errors='replace')
        # PostgreSQL не хранит нулевой символ в TEXT
        return str(value).replace('\x00', '')

    return value


def copy_table(sqlite_conn: sqlite3.Connection, pg_conn, table: str,
               skip_ids: Sequence[str]) -> Tuple[int, int]:
    """
    Копирует таблицу из SQLite в PostgreSQL.

    Returns:
        (перенесено строк, пропущено строк)
    """
    source_columns = table_columns(sqlite_conn, table, is_postgres=False)
    target_types = postgres_column_types(pg_conn, table)
    target_columns = set(target_types)

    columns = [column for column in source_columns if column in target_columns]
    ignored = [column for column in source_columns if column not in target_columns]
    if ignored:
        print(f"   ⚠️  {table}: колонок нет в PostgreSQL, пропущены: {', '.join(ignored)}")

    key_column = columns[0]
    skip = set(skip_ids)
    placeholders = ', '.join('?' for _ in columns)
    insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

    copied = 0
    skipped = 0
    batch: List[Tuple[Any, ...]] = []
    pg_cursor = pg_conn.cursor()

    for row in sqlite_conn.execute(f"SELECT {', '.join(columns)} FROM {table}"):
        if str(row[key_column]) in skip:
            skipped += 1
            continue

        batch.append(tuple(
            normalize_value(table, column, row[column], target_types[column]) for column in columns
        ))
        if len(batch) >= BATCH_SIZE:
            pg_cursor.executemany(insert_sql, batch)
            copied += len(batch)
            batch = []

    if batch:
        pg_cursor.executemany(insert_sql, batch)
        copied += len(batch)

    return copied, skipped


def reset_identity(pg_conn) -> None:
    """Сдвигает счётчик id публикаций за максимальный перенесённый идентификатор"""
    cursor = pg_conn.cursor()
    cursor.execute(
        "SELECT setval(pg_get_serial_sequence('confluence_publications', 'id'), "
        "COALESCE((SELECT MAX(id) FROM confluence_publications), 0) + 1, false)"
    )


def migrate(sqlite_path: str, pg_config: Dict[str, Any], replace: bool = False,
            dry_run: bool = False, skip_orphans: bool = False) -> Dict[str, Dict[str, int]]:
    """
    Переносит данные из SQLite в PostgreSQL.

    Args:
        sqlite_path: путь к файлу SQLite
        pg_config: настройки PostgreSQL в формате раздела database из config.json
        replace: очистить таблицы PostgreSQL перед переносом
        dry_run: только проверить источник и приёмник, ничего не записывая
        skip_orphans: пропускать строки с нарушенными внешними ключами вместо остановки

    Returns:
        Отчёт по таблицам: {'users': {'source': N, 'copied': N, 'skipped': N}, ...}
    """
    sqlite_conn = open_sqlite_readonly(sqlite_path)
    try:
        present = sqlite_tables(sqlite_conn)
        tables = [table for table in TABLES if table in present]
        missing = [table for table in TABLES if table not in present]
        if 'users' not in tables or 'jobs' not in tables:
            raise MigrationError(
                f"В файле {sqlite_path} нет таблиц users и jobs — это не база Meeting Processor"
            )
        if missing:
            print(f"   ℹ️  В SQLite нет таблиц: {', '.join(missing)} — они останутся пустыми")

        source_counts = {table: count_rows(sqlite_conn, table) for table in tables}

        orphans = find_orphans(sqlite_conn, tables)
        if orphans and not skip_orphans:
            details = '; '.join(
                f"{table}: {len(ids)} (например, {', '.join(ids[:3])})" for table, ids in orphans.items()
            )
            raise MigrationError(
                "В SQLite есть строки, ссылающиеся на несуществующие записи — "
                f"PostgreSQL их не примет. {details}. "
                "Запустите с --skip-orphans, чтобы перенести данные без этих строк."
            )

        # Строки, зависящие от пропущенных задач, тоже пропускаются
        skip_ids: Dict[str, List[str]] = {table: list(ids) for table, ids in orphans.items()}
        if skip_ids.get('jobs') and 'confluence_publications' in tables:
            marks = ', '.join('?' for _ in skip_ids['jobs'])
            dependent = sqlite_conn.execute(
                f"SELECT id FROM confluence_publications WHERE job_id IN ({marks})", skip_ids['jobs']
            ).fetchall()
            skip_ids.setdefault('confluence_publications', []).extend(str(row[0]) for row in dependent)

        config = dict(pg_config)
        config['type'] = 'postgresql'
        conninfo = pg_adapter.build_conninfo(config)
        print(f"   ✅ Приёмник: {pg_adapter.describe_conninfo(conninfo)}")

        report: Dict[str, Dict[str, int]] = {}

        # Проверка приёмника до каких-либо изменений в нём
        with pg_adapter.connect(conninfo) as pg_conn:
            target_counts = postgres_row_counts(pg_conn)
        non_empty = {table: count for table, count in target_counts.items() if count}

        if non_empty and not replace:
            details = ', '.join(f"{table}: {count}" for table, count in non_empty.items())
            raise MigrationError(
                f"В PostgreSQL уже есть данные ({details}). "
                "Запустите с --replace, чтобы очистить таблицы перед переносом."
            )

        if dry_run:
            for table in tables:
                skipped = len(set(skip_ids.get(table, ())))
                report[table] = {
                    'source': source_counts[table],
                    'copied': source_counts[table] - skipped,
                    'skipped': skipped,
                }
            return report

        # Создаёт схему в PostgreSQL теми же миграциями, что и приложение
        manager = DatabaseManager(config)

        with manager._get_connection() as pg_conn:
            if non_empty:
                pg_conn.cursor().execute(
                    "TRUNCATE TABLE confluence_publications, jobs, users RESTART IDENTITY"
                )

            # Весь перенос идёт одной транзакцией: при ошибке PostgreSQL остаётся как был
            for table in tables:
                copied, skipped = copy_table(sqlite_conn, pg_conn, table, skip_ids.get(table, ()))
                report[table] = {'source': source_counts[table], 'copied': copied, 'skipped': skipped}

            reset_identity(pg_conn)

            # Сверка количества строк до фиксации транзакции
            for table in tables:
                actual = count_rows(pg_conn, table)
                expected = report[table]['copied']
                if actual != expected:
                    raise MigrationError(
                        f"Таблица {table}: в PostgreSQL {actual} строк, ожидалось {expected}"
                    )

        return report
    finally:
        sqlite_conn.close()


def load_app_config(config_file: str) -> Dict[str, Any]:
    """Читает config.json; отсутствие файла — не ошибка"""
    path = Path(config_file)
    if not path.is_file():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_sources(args, app_config: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Определяет путь к SQLite и настройки PostgreSQL из аргументов, окружения и config.json"""
    db_config = dict(app_config.get('database', {}))

    sqlite_path = args.sqlite or db_config.get('sqlite_path')
    if not sqlite_path:
        # database.path относится к SQLite, даже если тип уже переключён на postgresql
        sqlite_path = db_config.get('path') or 'meeting_processor.db'

    pg_config = {key: value for key, value in db_config.items() if key not in ('type', 'path')}
    if args.postgres_url:
        if not pg_adapter.is_postgres_url(args.postgres_url):
            raise MigrationError("--postgres-url должен начинаться с postgresql:// или postgres://")
        # Явный аргумент важнее DATABASE_URL из окружения
        os.environ[pg_adapter.DATABASE_URL_ENV_VAR] = args.postgres_url

    has_target = (
        pg_adapter.is_postgres_url(os.getenv(pg_adapter.DATABASE_URL_ENV_VAR))
        or pg_config.get('url') or pg_config.get('host')
    )
    if not has_target:
        raise MigrationError(
            "Не заданы параметры PostgreSQL. Укажите --postgres-url, переменную окружения "
            "DATABASE_URL или поля database.host / database.url в config.json."
        )

    return sqlite_path, pg_config


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description='Перенос данных Meeting Processor из SQLite в PostgreSQL'
    )
    parser.add_argument('--sqlite', help='Путь к файлу SQLite (по умолчанию database.path из config.json)')
    parser.add_argument('--postgres-url',
                        help='URL PostgreSQL вида postgresql://user:password@host:5432/dbname '
                             '(по умолчанию DATABASE_URL или раздел database из config.json)')
    parser.add_argument('--config', default='config.json', help='Файл конфигурации (по умолчанию config.json)')
    parser.add_argument('--replace', action='store_true',
                        help='Очистить таблицы PostgreSQL перед переносом, если в них уже есть данные')
    parser.add_argument('--skip-orphans', action='store_true',
                        help='Пропускать строки с нарушенными внешними ключами вместо остановки')
    parser.add_argument('--dry-run', action='store_true',
                        help='Проверить источник и приёмник, ничего не записывая в PostgreSQL')
    args = parser.parse_args(argv)

    print("🚚 Перенос данных из SQLite в PostgreSQL")
    print("=" * 50)

    try:
        if not pg_adapter.PSYCOPG_AVAILABLE:
            raise MigrationError('Не установлен драйвер PostgreSQL: pip install "psycopg[binary]"')

        sqlite_path, pg_config = resolve_sources(args, load_app_config(args.config))
        print(f"   Источник: {sqlite_path}")

        report = migrate(
            sqlite_path, pg_config,
            replace=args.replace, dry_run=args.dry_run, skip_orphans=args.skip_orphans
        )
    except MigrationError as e:
        print(f"\n❌ {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Ошибка переноса: {e}")
        return 1

    print("\n📊 Проверка (ничего не записано):" if args.dry_run else "\n📊 Перенесено:")
    for table, numbers in report.items():
        line = f"   • {table}: {numbers['copied']} из {numbers['source']}"
        if numbers['skipped']:
            line += f" (пропущено: {numbers['skipped']})"
        print(line)

    if args.dry_run:
        print("\n💡 Запустите без --dry-run, чтобы выполнить перенос.")
    else:
        print("\n🎉 Перенос завершён. Переключите приложение на PostgreSQL:")
        print('   config.json → "database": {"type": "postgresql", ...} или переменная DATABASE_URL')
    return 0


if __name__ == '__main__':
    sys.exit(main())
