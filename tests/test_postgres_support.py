#!/usr/bin/env python3
"""
Тесты поддержки PostgreSQL и переноса данных из SQLite.

Тесты без сервера (перевод плейсхолдеров, выбор СУБД, схема) выполняются всегда.
Тесты на настоящем PostgreSQL выполняются, только если задана переменная окружения
TEST_DATABASE_URL, например:

    TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

Каждый такой тест работает в собственной временной схеме и удаляет её за собой.
"""

import gc
import json
import os
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import pg_adapter
from database.db_manager import DatabaseManager
from database.models import DatabaseSchema, PublicationStatus

TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', '').strip()
POSTGRES_AVAILABLE = pg_adapter.PSYCOPG_AVAILABLE and pg_adapter.is_postgres_url(TEST_DATABASE_URL)

requires_postgres = unittest.skipUnless(
    POSTGRES_AVAILABLE, 'TEST_DATABASE_URL не задан или не установлен psycopg'
)


def without_database_env():
    """Убирает DATABASE_URL и DATABASE_PASSWORD из окружения на время теста"""
    patcher = patch.dict(os.environ)
    patcher.start()
    os.environ.pop(pg_adapter.DATABASE_URL_ENV_VAR, None)
    os.environ.pop(pg_adapter.DATABASE_PASSWORD_ENV_VAR, None)
    return patcher


class TestPlaceholderTranslation(unittest.TestCase):
    """Перевод SQL из диалекта SQLite в диалект psycopg"""

    def test_placeholders_are_translated(self):
        self.assertEqual(
            pg_adapter.translate_placeholders("SELECT * FROM jobs WHERE job_id = ? AND user_id = ?"),
            "SELECT * FROM jobs WHERE job_id = %s AND user_id = %s"
        )

    def test_question_mark_inside_literal_is_kept(self):
        self.assertEqual(
            pg_adapter.translate_placeholders("UPDATE jobs SET message = 'Готово?' WHERE job_id = ?"),
            "UPDATE jobs SET message = 'Готово?' WHERE job_id = %s"
        )

    def test_percent_is_escaped(self):
        self.assertEqual(
            pg_adapter.translate_placeholders("SELECT * FROM jobs WHERE filename LIKE '%.mp3' AND user_id = ?"),
            "SELECT * FROM jobs WHERE filename LIKE '%%.mp3' AND user_id = %s"
        )
        self.assertEqual(pg_adapter.translate_placeholders("SELECT 10 % 3, ?"), "SELECT 10 %% 3, %s")

    def test_escaped_quote_inside_literal(self):
        self.assertEqual(
            pg_adapter.translate_placeholders("SELECT 'it''s ?' , ?"),
            "SELECT 'it''s ?' , %s"
        )

    def test_quoted_identifier_is_kept(self):
        self.assertEqual(
            pg_adapter.translate_placeholders('SELECT "what?" FROM t WHERE a = ?'),
            'SELECT "what?" FROM t WHERE a = %s'
        )


class TestDatabaseTypeResolution(unittest.TestCase):
    """Выбор СУБД по конфигурации и окружению"""

    def setUp(self):
        self.addCleanup(without_database_env().stop)

    def test_sqlite_is_default(self):
        self.assertEqual(pg_adapter.resolve_database_type({}), 'sqlite')
        self.assertEqual(pg_adapter.resolve_database_type({'type': 'sqlite'}), 'sqlite')
        self.assertEqual(pg_adapter.resolve_database_type({'type': None}), 'sqlite')

    def test_postgres_aliases(self):
        for alias in ('postgresql', 'postgres', 'PostgreSQL', ' pg '):
            with self.subTest(alias=alias):
                self.assertEqual(pg_adapter.resolve_database_type({'type': alias}), 'postgresql')

    def test_database_url_selects_postgres(self):
        os.environ['DATABASE_URL'] = 'postgresql://user@db:5432/meetings'
        self.assertEqual(pg_adapter.resolve_database_type({'type': 'sqlite'}), 'postgresql')

    def test_non_postgres_database_url_is_ignored(self):
        os.environ['DATABASE_URL'] = 'sqlite:///meeting_processor.db'
        self.assertEqual(pg_adapter.resolve_database_type({'type': 'sqlite'}), 'sqlite')

    @unittest.skipUnless(pg_adapter.PSYCOPG_AVAILABLE, 'psycopg не установлен')
    def test_conninfo_from_fields(self):
        from psycopg.conninfo import conninfo_to_dict

        conninfo = pg_adapter.build_conninfo({
            'host': 'db.example.com', 'port': 5433, 'name': 'meetings',
            'user': 'meeting', 'password': 'from_config', 'sslmode': 'require'
        })
        params = conninfo_to_dict(conninfo)

        self.assertEqual(params['host'], 'db.example.com')
        self.assertEqual(str(params['port']), '5433')
        self.assertEqual(params['dbname'], 'meetings')
        self.assertEqual(params['user'], 'meeting')
        self.assertEqual(params['password'], 'from_config')
        self.assertEqual(params['sslmode'], 'require')

    @unittest.skipUnless(pg_adapter.PSYCOPG_AVAILABLE, 'psycopg не установлен')
    def test_password_from_environment_overrides_config(self):
        from psycopg.conninfo import conninfo_to_dict

        os.environ['DATABASE_PASSWORD'] = 'from_env'
        conninfo = pg_adapter.build_conninfo({'host': 'db', 'user': 'meeting', 'password': 'from_config'})

        self.assertEqual(conninfo_to_dict(conninfo)['password'], 'from_env')

    @unittest.skipUnless(pg_adapter.PSYCOPG_AVAILABLE, 'psycopg не установлен')
    def test_database_url_overrides_config_and_password_is_not_logged(self):
        os.environ['DATABASE_URL'] = 'postgresql://meeting:secret@db.internal:5432/meetings'
        conninfo = pg_adapter.build_conninfo({'host': 'ignored', 'name': 'ignored'})
        description = pg_adapter.describe_conninfo(conninfo)

        self.assertEqual(description, 'postgresql://meeting@db.internal:5432/meetings')
        self.assertNotIn('secret', description)


class TestSchemaDialects(unittest.TestCase):
    """Схема и выражения SQL для двух СУБД"""

    def test_postgres_migrations_cover_same_versions(self):
        for version in (1, 2, 3):
            with self.subTest(version=version):
                self.assertTrue(DatabaseSchema.get_migration_sql(version, 'postgresql'))
                self.assertTrue(DatabaseSchema.get_migration_sql(version, 'sqlite'))

    def test_postgres_migrations_have_no_sqlite_syntax(self):
        sql = '\n'.join(
            statement for version in (1, 2, 3)
            for statement in DatabaseSchema.get_migration_sql(version, 'postgresql')
        )
        self.assertNotIn('AUTOINCREMENT', sql)
        self.assertNotIn('TRIGGER IF NOT EXISTS', sql)
        self.assertIn('GENERATED BY DEFAULT AS IDENTITY', sql)

    def test_sqlite_remains_default_dialect(self):
        self.assertEqual(DatabaseSchema.get_migration_sql(3), DatabaseSchema.get_migration_sql(3, 'sqlite'))
        self.assertIn('AUTOINCREMENT', DatabaseSchema.get_migration_sql(3)[0])

    def test_sqlite_date_expressions(self):
        self.addCleanup(without_database_env().stop)
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        self.addCleanup(lambda: (gc.collect(), os.unlink(db_file.name)))

        manager = DatabaseManager({'path': db_file.name})

        self.assertEqual(manager.db_type, 'sqlite')
        self.assertEqual(manager.sql_days_ago(30), "datetime('now', '-30 days')")
        self.assertEqual(manager.sql_next_day(), "datetime(?, '+1 day')")
        self.assertEqual(manager.get_database_info()['db_type'], 'sqlite')


class PostgresTestCase(unittest.TestCase):
    """База для тестов на настоящем PostgreSQL: отдельная схема на каждый тест"""

    def setUp(self):
        import psycopg
        from psycopg.conninfo import make_conninfo

        self.addCleanup(without_database_env().stop)

        self.schema = f"mp_test_{uuid.uuid4().hex[:12]}"
        with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
            conn.execute(f'CREATE SCHEMA "{self.schema}"')
        self.addCleanup(self._drop_schema)

        self.pg_url = make_conninfo(TEST_DATABASE_URL, options=f"-c search_path={self.schema}")
        self.pg_config = {'type': 'postgresql', 'url': self.pg_url}

    def _drop_schema(self):
        import psycopg

        gc.collect()
        with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE')

    def make_manager(self) -> DatabaseManager:
        return DatabaseManager(dict(self.pg_config))

    @staticmethod
    def add_user(manager, user_id='user_1', **extra):
        data = {'user_id': user_id, 'email': f'{user_id}@example.com', 'name': f'Name {user_id}'}
        data.update(extra)
        return manager.create_user(data)

    @staticmethod
    def add_job(manager, job_id='job_1', user_id='user_1', **extra):
        data = {'job_id': job_id, 'user_id': user_id, 'filename': f'{job_id}.mp3',
                'template': 'standard', 'status': 'completed', 'progress': 100}
        data.update(extra)
        return manager.create_job(data)

    @staticmethod
    def add_publication(manager, job_id='job_1', page_id='page_1', **extra):
        data = {'job_id': job_id, 'confluence_page_id': page_id,
                'confluence_page_url': f'https://wiki.example.com/pages/{page_id}',
                'confluence_space_key': 'TEST', 'page_title': f'Title {page_id}',
                'publication_status': PublicationStatus.PUBLISHED}
        data.update(extra)
        return manager.create_confluence_publication(data)


@requires_postgres
class TestPostgresDatabaseManager(PostgresTestCase):
    """DatabaseManager поверх PostgreSQL"""

    def test_migrations_create_schema_and_are_idempotent(self):
        manager = self.make_manager()
        self.assertEqual(manager.db_type, 'postgresql')
        self.assertNotIn('password', manager.db_path)

        # Повторная инициализация (второй worker gunicorn) ничего не ломает
        second = self.make_manager()

        with second._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
            )
            tables = {row[0] for row in cursor.fetchall()}
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
            versions = [row[0] for row in cursor.fetchall()]

        self.assertTrue({'users', 'jobs', 'confluence_publications', 'schema_migrations'} <= tables)
        self.assertEqual(versions, [1, 2, 3])

    def test_concurrent_initialization(self):
        """Несколько процессов (workers gunicorn) создают схему одновременно"""
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=6) as pool:
            managers = list(pool.map(lambda _: self.make_manager(), range(6)))

        with managers[0]._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
            self.assertEqual([row[0] for row in cursor.fetchall()], [1, 2, 3])

    def test_user_and_job_crud(self):
        manager = self.make_manager()

        user = self.add_user(manager, full_name='Полное Имя')
        self.assertEqual(user['email'], 'user_1@example.com')
        self.assertEqual(user['full_name'], 'Полное Имя')
        # Даты возвращаются строками, как в SQLite
        self.assertRegex(user['created_at'], r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
        self.assertIsNone(user['last_login'])

        with self.assertRaises(ValueError):
            self.add_user(manager)

        self.assertTrue(manager.update_user_info('user_1', {'user_id': 'user_1', 'name': 'Новое имя'}))
        self.assertTrue(manager.update_user_last_login('user_1'))
        user = manager.get_user_by_id('user_1')
        self.assertEqual(user['name'], 'Новое имя')
        self.assertIsNotNone(user['last_login'])

        job = self.add_job(manager, metadata={'model': 'm', 'participants': [{'full_name': 'Иван'}]})
        self.assertEqual(job['progress'], 100)
        self.assertEqual(json.loads(job['metadata'])['participants'][0]['full_name'], 'Иван')

        self.assertIsNone(manager.get_job_by_id('job_1', 'other_user'))
        self.assertTrue(manager.update_job('job_1', {'status': 'error', 'progress': 0, 'error': 'сбой'}))
        self.assertEqual(manager.get_job_by_id('job_1', 'user_1')['error'], 'сбой')

        self.add_job(manager, 'job_2', status='processing', progress=50)
        self.assertEqual(len(manager.get_user_jobs('user_1')), 2)
        self.assertEqual(len(manager.get_user_jobs('user_1', status='processing')), 1)
        self.assertEqual(len(manager.get_user_jobs('user_1', limit=1, offset=1)), 1)
        self.assertEqual(manager.get_all_jobs(limit=5)[0]['user_display'], 'Новое имя')

        self.assertTrue(manager.delete_job('job_2', 'user_1'))
        self.assertFalse(manager.delete_job('job_2'))

    def test_row_access_matches_sqlite(self):
        manager = self.make_manager()
        self.add_user(manager)

        with manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, email FROM users WHERE user_id = ?", ('user_1',))
            row = cursor.fetchone()

            self.assertEqual(row[0], 'user_1')
            self.assertEqual(row['email'], 'user_1@example.com')
            self.assertEqual(dict(row), {'user_id': 'user_1', 'email': 'user_1@example.com'})
            self.assertEqual(row.keys(), ['user_id', 'email'])

        # with закрывает соединение PostgreSQL
        self.assertTrue(conn.closed)

    def test_raw_sql_used_by_web_app(self):
        """Запросы в том виде, в котором их выполняет run_web.py"""
        manager = self.make_manager()
        self.add_user(manager)
        self.add_job(manager, status='processing', progress=10)

        with manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET progress = ?, message = ? WHERE job_id = ?",
                           (55, 'Транскрибация: 55%', 'job_1'))
            conn.commit()

        with manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs SET
                    status = 'completed',
                    progress = 100,
                    message = 'Протокол успешно сгенерирован!',
                    transcript_file = ?,
                    summary_file = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, ('/tmp/t.txt', '/tmp/s.md', 'job_1'))
            conn.commit()

        with manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", ('job_1',))
            job = dict(cursor.fetchone())
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE filename LIKE '%.mp3' AND user_id = ?", ('user_1',))
            matched = cursor.fetchone()[0]

        self.assertEqual(job['status'], 'completed')
        self.assertEqual(job['summary_file'], '/tmp/s.md')
        self.assertIsNotNone(job['completed_at'])
        self.assertEqual(matched, 1)

    def test_failed_statement_rolls_back(self):
        manager = self.make_manager()
        self.add_user(manager)

        with self.assertRaises(Exception):
            with manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", ('Changed', 'user_1'))
                cursor.execute("SELECT * FROM table_that_does_not_exist")

        self.assertEqual(manager.get_user_by_id('user_1')['name'], 'Name user_1')

    def test_confluence_publications(self):
        manager = self.make_manager()
        self.add_user(manager)
        self.add_job(manager)

        first = self.add_publication(manager, page_id='page_1')
        second = self.add_publication(manager, page_id='page_2',
                                      publication_status=PublicationStatus.FAILED, error_message='timeout')
        self.assertIsInstance(first['id'], int)
        self.assertEqual(second['id'], first['id'] + 1)

        # Уникальность (job_id, confluence_page_id)
        with self.assertRaises(Exception):
            self.add_publication(manager, page_id='page_1')

        publications = manager.get_confluence_publications('job_1', 'user_1')
        self.assertEqual({p['page_id'] for p in publications}, {'page_1', 'page_2'})
        self.assertEqual(manager.get_confluence_publications('job_1', 'other_user'), [])
        self.assertEqual(len(manager.get_confluence_publications_by_status(PublicationStatus.FAILED, limit=5)), 1)

        # Триггер обновляет updated_at
        time.sleep(1.1)
        self.assertTrue(manager.update_confluence_publication(first['id'], {'error_message': 'retry'}))
        updated = manager.get_confluence_publication_by_id(first['id'])
        self.assertEqual(updated['created_at'], first['created_at'])
        self.assertNotEqual(updated['updated_at'], first['updated_at'])

        stats = manager.get_confluence_publications_statistics()
        self.assertEqual(stats['overall']['total_publications'], 2)
        self.assertEqual(stats['overall']['published_count'], 1)
        self.assertEqual(stats['overall']['failed_count'], 1)
        self.assertIsInstance(stats['overall']['avg_retry_count'], float)
        self.assertEqual(stats['by_space'][0]['publications_count'], 2)
        self.assertEqual(stats['daily'][0]['publications_count'], 2)
        self.assertRegex(stats['daily'][0]['date'], r'^\d{4}-\d{2}-\d{2}$')

        # Каскадное удаление публикаций вместе с задачей
        self.assertTrue(manager.delete_job('job_1'))
        self.assertIsNone(manager.get_confluence_publication_by_id(first['id']))

    def test_statistics(self):
        manager = self.make_manager()
        self.add_user(manager, 'user_1')
        self.add_user(manager, 'user_2')
        self.add_job(manager, 'job_1', 'user_1')
        self.add_job(manager, 'job_2', 'user_1', status='error', progress=0, template='business')
        self.add_job(manager, 'job_3', 'user_2', status='processing', progress=30)

        # Старая задача за пределами периода
        self.add_job(manager, 'job_old', 'user_2')
        with manager._get_connection() as conn:
            conn.cursor().execute("UPDATE jobs SET created_at = ? WHERE job_id = ?",
                                  ('2020-01-15 10:00:00', 'job_old'))
            conn.commit()

        stats = manager.get_usage_statistics(days_back=7)
        self.assertEqual(stats['overall']['total_protocols'], 3)
        self.assertEqual(stats['overall']['unique_users'], 2)
        self.assertEqual(stats['overall']['completed_protocols'], 1)
        self.assertEqual(stats['overall']['failed_protocols'], 1)
        self.assertEqual(stats['daily'][0]['protocols_count'], 3)
        self.assertRegex(stats['daily'][0]['date'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertEqual({u['user_id']: u['protocols_count'] for u in stats['users']}, {'user_1': 2, 'user_2': 1})
        # Шаблон страницы берёт срез last_activity[:10]
        self.assertRegex(stats['users'][0]['last_activity'][:10], r'^\d{4}-\d{2}-\d{2}$')
        self.assertEqual({t['template']: t['usage_count'] for t in stats['templates']},
                         {'standard': 2, 'business': 1})

        # Период по датам: граница конца включается целиком
        stats = manager.get_usage_statistics(start_date='2020-01-01', end_date='2020-01-15')
        self.assertEqual(stats['overall']['total_protocols'], 1)
        stats = manager.get_usage_statistics(start_date='2020-01-01', end_date='2020-01-14')
        self.assertEqual(stats['overall']['total_protocols'], 0)

        self.assertEqual(manager.get_usage_statistics()['overall']['total_protocols'], 3)

        user_stats = manager.get_user_job_stats('user_1')
        self.assertEqual(user_stats['total_jobs'], 2)
        self.assertEqual(user_stats['failed_jobs'], 1)

        self.assertEqual(manager.cleanup_old_jobs('user_2', days_old=30), 1)
        self.assertIsNone(manager.get_job_by_id('job_old'))

        info = manager.get_database_info()
        self.assertEqual(info['db_type'], 'postgresql')
        self.assertEqual(info['users_count'], 2)
        self.assertEqual(info['jobs_count'], 3)
        self.assertGreater(info['db_size_bytes'], 0)

    def test_backup_is_not_supported(self):
        with self.assertRaises(NotImplementedError):
            self.make_manager().backup_database()


@requires_postgres
class TestSqliteToPostgresMigration(PostgresTestCase):
    """Перенос данных скриптом migrate_sqlite_to_postgres.py"""

    def setUp(self):
        super().setUp()
        sqlite_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        sqlite_file.close()
        self.sqlite_path = sqlite_file.name
        self.addCleanup(self._remove_sqlite)

        source = DatabaseManager({'type': 'sqlite', 'path': self.sqlite_path})
        self.add_user(source, 'user_1', full_name='Иван Петров')
        self.add_user(source, 'user_2')
        self.add_job(source, 'job_1', 'user_1', metadata={'participants': [{'full_name': 'Иван Петров'}]})
        self.add_job(source, 'job_2', 'user_1', status='error', progress=0, error='Ошибка «кавычки» 100%')
        self.add_job(source, 'job_3', 'user_2', status='processing', progress=40)
        self.add_publication(source, 'job_1', 'page_1')
        self.add_publication(source, 'job_1', 'page_2', publication_status=PublicationStatus.FAILED,
                             error_message='timeout')

        # Данные в том виде, в каком они встречаются в реальных базах SQLite
        with source._get_connection() as conn:
            conn.execute("UPDATE jobs SET created_at = '2025-03-01T08:30:15.123456', completed_at = '' "
                         "WHERE job_id = 'job_2'")
            conn.execute("UPDATE jobs SET progress = '40' WHERE job_id = 'job_3'")
            conn.execute("UPDATE users SET last_login = '2025-03-02 09:00:00' WHERE user_id = 'user_1'")
            # Идентификаторы публикаций с пропуском
            conn.execute("UPDATE confluence_publications SET id = 41 WHERE confluence_page_id = 'page_2'")
            conn.commit()
        conn.close()
        self.source = source

    def _remove_sqlite(self):
        self.source = None
        gc.collect()
        try:
            os.unlink(self.sqlite_path)
        except FileNotFoundError:
            pass

    def migrate(self, **kwargs):
        import migrate_sqlite_to_postgres as migration
        return migration.migrate(self.sqlite_path, {'url': self.pg_url}, **kwargs)

    def test_data_is_copied(self):
        report = self.migrate()

        self.assertEqual(report['users'], {'source': 2, 'copied': 2, 'skipped': 0})
        self.assertEqual(report['jobs'], {'source': 3, 'copied': 3, 'skipped': 0})
        self.assertEqual(report['confluence_publications'], {'source': 2, 'copied': 2, 'skipped': 0})

        target = self.make_manager()

        user = target.get_user_by_id('user_1')
        self.assertEqual(user['full_name'], 'Иван Петров')
        self.assertEqual(user['last_login'], '2025-03-02 09:00:00')
        self.assertEqual(user['created_at'], self.source.get_user_by_id('user_1')['created_at'])

        job = target.get_job_by_id('job_1')
        self.assertEqual(json.loads(job['metadata'])['participants'][0]['full_name'], 'Иван Петров')
        self.assertEqual(job['created_at'], self.source.get_job_by_id('job_1')['created_at'])

        job = target.get_job_by_id('job_2')
        self.assertEqual(job['error'], 'Ошибка «кавычки» 100%')
        self.assertEqual(job['created_at'], '2025-03-01 08:30:15')
        self.assertIsNone(job['completed_at'])

        self.assertEqual(target.get_job_by_id('job_3')['progress'], 40)

        publications = {p['confluence_page_id']: p for p in target.get_all_confluence_publications()}
        self.assertEqual(publications['page_2']['id'], 41)
        self.assertEqual(publications['page_2']['error_message'], 'timeout')

        # Счётчик идентификаторов продолжает после максимального перенесённого
        self.add_job(target, 'job_new', 'user_2')
        self.assertEqual(self.add_publication(target, 'job_new', 'page_new')['id'], 42)

    def test_source_is_not_modified(self):
        before = os.path.getsize(self.sqlite_path), os.path.getmtime(self.sqlite_path)
        self.migrate()
        self.assertEqual((os.path.getsize(self.sqlite_path), os.path.getmtime(self.sqlite_path)), before)
        self.assertEqual(len(self.source.get_all_jobs()), 3)

    def test_non_empty_target_requires_replace(self):
        import migrate_sqlite_to_postgres as migration

        self.migrate()
        with self.assertRaises(migration.MigrationError):
            self.migrate()

        # --replace очищает приёмник и переносит данные заново
        target = self.make_manager()
        self.add_job(target, 'job_extra', 'user_2')
        report = self.migrate(replace=True)

        self.assertEqual(report['jobs']['copied'], 3)
        self.assertIsNone(target.get_job_by_id('job_extra'))
        self.assertEqual(len(target.get_all_jobs()), 3)

    def test_dry_run_writes_nothing(self):
        report = self.migrate(dry_run=True)
        self.assertEqual(report['jobs'], {'source': 3, 'copied': 3, 'skipped': 0})

        import psycopg
        with psycopg.connect(self.pg_url) as conn:
            tables = conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = current_schema()"
            ).fetchone()[0]
        self.assertEqual(tables, 0)

    def test_orphan_rows(self):
        import migrate_sqlite_to_postgres as migration
        import sqlite3

        # Задача без пользователя и её публикация: в SQLite такое возможно при выключенных внешних ключах
        conn = sqlite3.connect(self.sqlite_path)
        conn.execute("INSERT INTO jobs (job_id, user_id, filename, template) VALUES ('job_orphan', 'ghost', 'o.mp3', 'standard')")
        conn.execute("INSERT INTO confluence_publications (job_id, confluence_page_id, confluence_page_url, "
                     "confluence_space_key, page_title) VALUES ('job_orphan', 'p', 'https://w/p', 'S', 'T')")
        conn.commit()
        conn.close()

        with self.assertRaises(migration.MigrationError) as context:
            self.migrate()
        self.assertIn('job_orphan', str(context.exception))

        # Ошибка возникла до записи: приёмник пуст
        self.assertEqual(self.migrate(dry_run=True, skip_orphans=True)['jobs']['skipped'], 1)

        report = self.migrate(skip_orphans=True)
        self.assertEqual(report['jobs'], {'source': 4, 'copied': 3, 'skipped': 1})
        self.assertEqual(report['confluence_publications'], {'source': 3, 'copied': 2, 'skipped': 1})
        self.assertIsNone(self.make_manager().get_job_by_id('job_orphan'))

    def test_command_line(self):
        import migrate_sqlite_to_postgres as migration

        missing_config = os.path.join(tempfile.gettempdir(), f'no_config_{uuid.uuid4().hex}.json')
        separator = '&' if '?' in TEST_DATABASE_URL else '?'
        url = f"{TEST_DATABASE_URL}{separator}options=-csearch_path%3D{self.schema}"

        # Не задан приёмник
        self.assertEqual(migration.main(['--sqlite', self.sqlite_path, '--config', missing_config]), 1)
        # Нет файла-источника
        self.assertEqual(migration.main(['--sqlite', 'no_such_file.db', '--postgres-url', url,
                                         '--config', missing_config]), 1)
        # --postgres-url должен быть URL
        self.assertEqual(migration.main(['--sqlite', self.sqlite_path, '--postgres-url', 'host=localhost',
                                         '--config', missing_config]), 1)
        self.assertEqual(len(self.make_manager().get_all_jobs()), 0)

        self.assertEqual(migration.main(['--sqlite', self.sqlite_path, '--postgres-url', url,
                                         '--config', missing_config]), 0)
        self.assertEqual(len(self.make_manager().get_all_jobs()), 3)


@requires_postgres
class TestFlaskAppOnPostgres(PostgresTestCase):
    """Веб-приложение с базой PostgreSQL"""

    def setUp(self):
        super().setUp()
        from run_web import WorkingMeetingWebApp

        self.user = {'user_id': 'pg_user', 'email': 'pg@example.com', 'name': 'PG User'}
        config = {
            'database': dict(self.pg_config),
            'auth': {'enabled': True, 'debug_mode': True, 'debug_user': self.user},
            'confluence': {'enabled': False},
            'settings': {'max_file_size_mb': 200},
        }

        with patch.dict(os.environ, {'AUTH_DEBUG_MODE': 'true'}), \
             patch('run_web.ConfigLoader.load_config', return_value=config), \
             patch('run_web.ConfigLoader.load_api_keys', return_value={}), \
             patch('run_web.ConfigLoader.validate_api_keys', return_value=(True, True, 'k', 'k')):
            self.app = WorkingMeetingWebApp('test_config.json')
        self.client = self.app.app.test_client()
        self.addCleanup(self._shutdown_app)

        self.add_user(self.app.db_manager, 'pg_user', name='PG User')

    def _shutdown_app(self):
        self.app.executor.shutdown(wait=True)
        self.client = None
        self.app = None

    def test_pages_and_api(self):
        self.add_job(self.app.db_manager, 'pg_job', 'pg_user', summary_file='/tmp/s.md')
        self.add_job(self.app.db_manager, 'pg_job_2', 'pg_user', status='processing', progress=50)

        health = json.loads(self.client.get('/health').data)
        self.assertEqual(health['status'], 'healthy')
        self.assertEqual(health['database']['type'], 'postgresql')
        self.assertEqual(health['database']['jobs_count'], 2)

        response = self.client.get('/jobs')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'pg_job.mp3', response.data)
        self.assertIn('Завершено'.encode('utf-8'), response.data)

        status = json.loads(self.client.get('/api/status/pg_job_2').data)
        self.assertEqual(status['progress'], 50)
        self.assertEqual(status['stage'], 'transcribing')

        self.assertEqual(self.client.get('/status/pg_job').status_code, 200)
        self.assertEqual(self.client.get('/statistics').status_code, 200)
        self.assertEqual(self.client.get('/statistics?start_date=2020-01-01&end_date=2099-01-01').status_code, 200)

    def test_statistics_export(self):
        self.add_job(self.app.db_manager, 'pg_job', 'pg_user')

        for query in ('', '?days=7', '?start_date=2020-01-01&end_date=2099-01-01'):
            with self.subTest(query=query):
                response = self.client.get(f'/statistics/export{query}')
                self.assertEqual(response.status_code, 200)
                self.assertIn('spreadsheetml', response.headers.get('Content-Type', ''))
                response.close()

    def test_protocol_regeneration_creates_job(self):
        transcript = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_transcript.txt', encoding='utf-8')
        transcript.write('Спикер 0: тест')
        transcript.close()
        self.addCleanup(os.unlink, transcript.name)

        self.add_job(self.app.db_manager, 'pg_job', 'pg_user', transcript_file=transcript.name,
                     metadata={'participants': [{'full_name': 'Иван Петров', 'company': '', 'position': ''}]})

        with patch.object(self.app, 'generate_protocol_sync'):
            response = self.client.post('/generate_protocol/pg_job', data={'new_template': 'business'})

        self.assertEqual(response.status_code, 302)
        new_job = self.app.db_manager.get_job_by_id('pg_job_protocol_business')
        self.assertEqual(new_job['status'], 'processing')
        self.assertEqual(json.loads(new_job['metadata'])['participants'][0]['full_name'], 'Иван Петров')


if __name__ == '__main__':
    unittest.main()
