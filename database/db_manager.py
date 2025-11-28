#!/usr/bin/env python3
"""
Менеджер базы данных для системы обработки встреч
"""

import sqlite3
import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import threading

from .models import User, Job, ConfluencePublication, DatabaseSchema, DatabaseValidator

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных SQLite"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация менеджера базы данных
        
        Args:
            config: Конфигурация базы данных
        """
        self.config = config
        self.db_path = config.get('path', 'meeting_processor.db')
        self.backup_enabled = config.get('backup_enabled', True)
        self.backup_interval_hours = config.get('backup_interval_hours', 24)
        
        # Thread lock для безопасности
        self._lock = threading.Lock()
        
        # Инициализируем базу данных
        self._init_database()
        
        logger.info(f"Инициализирован менеджер базы данных: {self.db_path}")
    
    def _init_database(self):
        """Инициализирует базу данных"""
        try:
            # Создаем директорию если не существует
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Выполняем миграции (они включают создание таблиц и индексов)
            self._run_migrations()
            
            logger.info("База данных успешно инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
    
    def _create_tables(self):
        """Создает таблицы в базе данных"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for sql in DatabaseSchema.get_create_tables_sql():
                cursor.execute(sql)
            
            conn.commit()
    
    def _create_indexes(self):
        """Создает индексы в базе данных"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for sql in DatabaseSchema.get_create_indexes_sql():
                cursor.execute(sql)
            
            conn.commit()
    
    def _run_migrations(self):
        """Выполняет миграции базы данных"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Создаем таблицу для отслеживания миграций если не существует
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Проверяем какие миграции уже применены
                cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
                applied_migrations = {row[0] for row in cursor.fetchall()}
                
                # Список доступных миграций
                available_migrations = [1, 2, 3]  # Базовые таблицы, индексы, Confluence
                
                # Применяем недостающие миграции
                for version in available_migrations:
                    if version not in applied_migrations:
                        logger.info(f"Применение миграции версии {version}")
                        
                        migration_sqls = DatabaseSchema.get_migration_sql(version)
                        for sql in migration_sqls:
                            if sql.strip():  # Пропускаем пустые SQL
                                cursor.execute(sql)
                        
                        # Отмечаем миграцию как примененную
                        cursor.execute(
                            "INSERT INTO schema_migrations (version) VALUES (?)",
                            (version,)
                        )
                        
                        logger.info(f"Миграция версии {version} успешно применена")
                
                conn.commit()
                logger.info("Все миграции успешно применены")
                
        except Exception as e:
            logger.error(f"Ошибка выполнения миграций: {e}")
            raise
    
    def _get_connection(self) -> sqlite3.Connection:
        """Получает соединение с базой данных"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
        conn.execute("PRAGMA foreign_keys = ON")  # Включаем внешние ключи
        return conn
    
    # Методы для работы с пользователями
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает нового пользователя
        
        Args:
            user_data: Данные пользователя
            
        Returns:
            Созданный пользователь
        """
        if not DatabaseValidator.validate_user_data(user_data):
            raise ValueError("Невалидные данные пользователя")
        
        sanitized_data = DatabaseValidator.sanitize_user_data(user_data)
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, не существует ли уже пользователь
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (sanitized_data['user_id'],))
                if cursor.fetchone():
                    raise ValueError(f"Пользователь {sanitized_data['user_id']} уже существует")
                
                # Создаем пользователя
                columns = list(sanitized_data.keys())
                placeholders = ', '.join(['?' for _ in columns])
                values = [sanitized_data[col] for col in columns]
                
                sql = f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})"
                cursor.execute(sql, values)
                conn.commit()
                
                logger.info(f"Создан пользователь: {sanitized_data['user_id']}")
                
                # Возвращаем созданного пользователя
                return self.get_user_by_id(sanitized_data['user_id'])
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по ID
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Данные пользователя или None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def update_user_info(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """
        Обновляет информацию о пользователе
        
        Args:
            user_id: Идентификатор пользователя
            user_data: Новые данные пользователя
            
        Returns:
            True если обновление успешно
        """
        sanitized_data = DatabaseValidator.sanitize_user_data(user_data)
        
        # Убираем user_id из данных для обновления
        sanitized_data.pop('user_id', None)
        
        if not sanitized_data:
            return True  # Нечего обновлять
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                columns = list(sanitized_data.keys())
                set_clause = ', '.join([f"{col} = ?" for col in columns])
                values = [sanitized_data[col] for col in columns] + [user_id]
                
                sql = f"UPDATE users SET {set_clause} WHERE user_id = ?"
                cursor.execute(sql, values)
                conn.commit()
                
                return cursor.rowcount > 0
    
    def update_user_last_login(self, user_id: str) -> bool:
        """
        Обновляет время последнего входа пользователя
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            True если обновление успешно
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
    
    # Методы для работы с задачами
    
    def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает новую задачу
        
        Args:
            job_data: Данные задачи
            
        Returns:
            Созданная задача
        """
        if not DatabaseValidator.validate_job_data(job_data):
            raise ValueError("Невалидные данные задачи")
        
        sanitized_data = DatabaseValidator.sanitize_job_data(job_data)
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, не существует ли уже задача
                cursor.execute("SELECT job_id FROM jobs WHERE job_id = ?", (sanitized_data['job_id'],))
                if cursor.fetchone():
                    raise ValueError(f"Задача {sanitized_data['job_id']} уже существует")
                
                # Создаем задачу
                columns = list(sanitized_data.keys())
                placeholders = ', '.join(['?' for _ in columns])
                values = [sanitized_data[col] for col in columns]
                
                sql = f"INSERT INTO jobs ({', '.join(columns)}) VALUES ({placeholders})"
                cursor.execute(sql, values)
                conn.commit()
                
                logger.info(f"Создана задача: {sanitized_data['job_id']} для пользователя {sanitized_data['user_id']}")
                
                # Возвращаем созданную задачу
                return self.get_job_by_id(sanitized_data['job_id'])
    
    def get_job_by_id(self, job_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Получает задачу по ID
        
        Args:
            job_id: Идентификатор задачи
            user_id: Идентификатор пользователя (для проверки доступа)
            
        Returns:
            Данные задачи или None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("SELECT * FROM jobs WHERE job_id = ? AND user_id = ?", (job_id, user_id))
            else:
                cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_user_jobs(self, user_id: str, status: Optional[str] = None, 
                      limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Получает задачи пользователя
        
        Args:
            user_id: Идентификатор пользователя
            status: Фильтр по статусу (опционально)
            limit: Лимит записей (опционально)
            offset: Смещение для пагинации
            
        Returns:
            Список задач пользователя
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            sql = "SELECT * FROM jobs WHERE user_id = ?"
            params = [user_id]
            
            if status:
                sql += " AND status = ?"
                params.append(status)
            
            sql += " ORDER BY created_at DESC"
            
            if limit:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def update_job(self, job_id: str, job_data: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        """
        Обновляет задачу
        
        Args:
            job_id: Идентификатор задачи
            job_data: Новые данные задачи
            user_id: Идентификатор пользователя (для проверки доступа)
            
        Returns:
            True если обновление успешно
        """
        # Убираем неизменяемые поля
        update_data = job_data.copy()
        for field in ['job_id', 'user_id', 'created_at']:
            update_data.pop(field, None)
        
        if not update_data:
            return True  # Нечего обновлять
        
        # Сериализуем metadata если есть
        if 'metadata' in update_data and isinstance(update_data['metadata'], dict):
            update_data['metadata'] = json.dumps(update_data['metadata'])
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                columns = list(update_data.keys())
                set_clause = ', '.join([f"{col} = ?" for col in columns])
                values = [update_data[col] for col in columns]
                
                if user_id:
                    sql = f"UPDATE jobs SET {set_clause} WHERE job_id = ? AND user_id = ?"
                    values.extend([job_id, user_id])
                else:
                    sql = f"UPDATE jobs SET {set_clause} WHERE job_id = ?"
                    values.append(job_id)
                
                cursor.execute(sql, values)
                conn.commit()
                
                return cursor.rowcount > 0
    
    def delete_job(self, job_id: str, user_id: Optional[str] = None) -> bool:
        """
        Удаляет задачу
        
        Args:
            job_id: Идентификатор задачи
            user_id: Идентификатор пользователя (для проверки доступа)
            
        Returns:
            True если удаление успешно
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if user_id:
                    cursor.execute("DELETE FROM jobs WHERE job_id = ? AND user_id = ?", (job_id, user_id))
                else:
                    cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
                
                conn.commit()
                return cursor.rowcount > 0
    
    # Статистика и аналитика
    
    def get_usage_statistics(self, days_back: Optional[int] = None,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает статистику использования приложения
        
        Args:
            days_back: Количество дней назад для анализа (для обратной совместимости)
            start_date: Дата начала периода в формате ISO (YYYY-MM-DD)
            end_date: Дата окончания периода в формате ISO (YYYY-MM-DD)
            
        Returns:
            Статистика использования
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Определяем диапазон дат
            if start_date and end_date:
                # Используем указанный диапазон дат
                date_filter = "created_at >= ? AND created_at < datetime(?, '+1 day')"
                date_filter_with_prefix = "j.created_at >= ? AND j.created_at < datetime(?, '+1 day')"
                date_params = (start_date, end_date)
                period_info = f"{start_date} - {end_date}"
            elif days_back:
                # Используем days_back для обратной совместимости
                date_filter = "created_at >= datetime('now', '-{} days')".format(days_back)
                date_filter_with_prefix = "j.created_at >= datetime('now', '-{} days')".format(days_back)
                date_params = ()
                period_info = f"{days_back} days"
            else:
                # По умолчанию 30 дней
                days_back = 30
                date_filter = "created_at >= datetime('now', '-30 days')"
                date_filter_with_prefix = "j.created_at >= datetime('now', '-30 days')"
                date_params = ()
                period_info = "30 days"
            
            # Общая статистика
            query = f"""
                SELECT
                    COUNT(*) as total_protocols,
                    COUNT(DISTINCT user_id) as unique_users,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_protocols,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_protocols
                FROM jobs
                WHERE {date_filter}
            """
            cursor.execute(query, date_params)
            overall_stats = dict(cursor.fetchone())
            
            # Статистика по дням
            query = f"""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as protocols_count,
                    COUNT(DISTINCT user_id) as users_count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count
                FROM jobs
                WHERE {date_filter}
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """
            cursor.execute(query, date_params)
            daily_stats = [dict(row) for row in cursor.fetchall()]
            
            # Статистика по пользователям
            query = f"""
                SELECT
                    j.user_id,
                    u.name,
                    u.email,
                    COUNT(*) as protocols_count,
                    SUM(CASE WHEN j.status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                    MAX(j.created_at) as last_activity
                FROM jobs j
                LEFT JOIN users u ON j.user_id = u.user_id
                WHERE {date_filter_with_prefix}
                GROUP BY j.user_id, u.name, u.email
                ORDER BY protocols_count DESC
            """
            cursor.execute(query, date_params)
            user_stats = [dict(row) for row in cursor.fetchall()]
            
            # Статистика по шаблонам
            query = f"""
                SELECT
                    template,
                    COUNT(*) as usage_count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count
                FROM jobs
                WHERE {date_filter}
                GROUP BY template
                ORDER BY usage_count DESC
            """
            cursor.execute(query, date_params)
            template_stats = [dict(row) for row in cursor.fetchall()]
            
            return {
                'overall': overall_stats,
                'daily': daily_stats,
                'users': user_stats,
                'templates': template_stats,
                'period_days': days_back,
                'start_date': start_date,
                'end_date': end_date,
                'period_info': period_info
            }
    
    def get_user_job_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Получает статистику задач пользователя
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Статистика задач
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_jobs,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_jobs,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_jobs,
                    SUM(CASE WHEN status IN ('uploaded', 'processing') THEN 1 ELSE 0 END) as processing_jobs,
                    MIN(created_at) as first_job_date,
                    MAX(created_at) as last_job_date
                FROM jobs 
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            return {
                'total_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'processing_jobs': 0,
                'first_job_date': None,
                'last_job_date': None
            }
    
    def cleanup_old_jobs(self, user_id: str, days_old: int = 30) -> int:
        """
        Удаляет старые завершенные задачи пользователя
        
        Args:
            user_id: Идентификатор пользователя
            days_old: Возраст задач в днях для удаления
            
        Returns:
            Количество удаленных задач
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM jobs 
                    WHERE user_id = ? 
                    AND status IN ('completed', 'error') 
                    AND created_at < ?
                """, (user_id, cutoff_date.isoformat()))
                
                conn.commit()
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    logger.info(f"Удалено {deleted_count} старых задач для пользователя {user_id}")
                
                return deleted_count
    
    # Методы для работы с публикациями Confluence
    
    def create_confluence_publication(self, publication_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает новую публикацию в Confluence
        
        Args:
            publication_data: Данные публикации
            
        Returns:
            Созданная публикация
        """
        if not DatabaseValidator.validate_confluence_publication_data(publication_data):
            raise ValueError("Невалидные данные публикации Confluence")
        
        sanitized_data = DatabaseValidator.sanitize_confluence_publication_data(publication_data)
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Создаем публикацию
                columns = list(sanitized_data.keys())
                placeholders = ', '.join(['?' for _ in columns])
                values = [sanitized_data[col] for col in columns]
                
                sql = f"INSERT INTO confluence_publications ({', '.join(columns)}) VALUES ({placeholders})"
                cursor.execute(sql, values)
                conn.commit()
                
                publication_id = cursor.lastrowid
                
                logger.info(f"Создана публикация Confluence: {publication_id} для задачи {sanitized_data['job_id']}")
                
                # Возвращаем созданную публикацию
                return self.get_confluence_publication_by_id(publication_id)
    
    def get_confluence_publication_by_id(self, publication_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает публикацию по ID
        
        Args:
            publication_id: ID публикации
            
        Returns:
            Данные публикации или None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM confluence_publications WHERE id = ?", (publication_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_confluence_publications_by_job_id(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Получает все публикации для задачи
        
        Args:
            job_id: ID задачи
            
        Returns:
            Список публикаций
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM confluence_publications WHERE job_id = ? ORDER BY created_at DESC",
                (job_id,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_confluence_publications(self, job_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает публикации Confluence для задачи с проверкой доступа пользователя
        
        Args:
            job_id: ID задачи
            user_id: ID пользователя для проверки доступа
            
        Returns:
            Список публикаций
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, что задача принадлежит пользователю
            cursor.execute("SELECT 1 FROM jobs WHERE job_id = ? AND user_id = ?", (job_id, user_id))
            if not cursor.fetchone():
                return []  # Нет доступа к задаче
            
            # Получаем публикации для задачи с маппингом полей для UI
            cursor.execute(
                """SELECT
                    id,
                    job_id,
                    page_title,
                    confluence_space_key as space_key,
                    confluence_page_url as page_url,
                    confluence_page_id as page_id,
                    publication_status as status,
                    error_message,
                    created_at
                FROM confluence_publications
                WHERE job_id = ?
                ORDER BY created_at DESC""",
                (job_id,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def update_confluence_publication(self, publication_id: int,
                                    publication_data: Dict[str, Any]) -> bool:
        """
        Обновляет публикацию
        
        Args:
            publication_id: ID публикации
            publication_data: Новые данные публикации
            
        Returns:
            True если обновление успешно
        """
        # Убираем неизменяемые поля
        update_data = publication_data.copy()
        for field in ['id', 'job_id', 'created_at']:
            update_data.pop(field, None)
        
        if not update_data:
            return True  # Нечего обновлять
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                columns = list(update_data.keys())
                set_clause = ', '.join([f"{col} = ?" for col in columns])
                values = [update_data[col] for col in columns] + [publication_id]
                
                sql = f"UPDATE confluence_publications SET {set_clause} WHERE id = ?"
                cursor.execute(sql, values)
                conn.commit()
                
                return cursor.rowcount > 0
    
    def delete_confluence_publication(self, publication_id: int) -> bool:
        """
        Удаляет публикацию
        
        Args:
            publication_id: ID публикации
            
        Returns:
            True если удаление успешно
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM confluence_publications WHERE id = ?", (publication_id,))
                conn.commit()
                return cursor.rowcount > 0
    
    def get_confluence_publications_by_status(self, status: str,
                                            limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получает публикации по статусу
        
        Args:
            status: Статус публикации
            limit: Лимит записей
            
        Returns:
            Список публикаций
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            sql = "SELECT * FROM confluence_publications WHERE publication_status = ? ORDER BY created_at DESC"
            params = [status]
            
            if limit:
                sql += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_confluence_publications_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику публикаций в Confluence
        
        Returns:
            Статистика публикаций
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute("""
                SELECT
                    COUNT(*) as total_publications,
                    SUM(CASE WHEN publication_status = 'published' THEN 1 ELSE 0 END) as published_count,
                    SUM(CASE WHEN publication_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                    SUM(CASE WHEN publication_status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                    SUM(CASE WHEN publication_status = 'retrying' THEN 1 ELSE 0 END) as retrying_count,
                    COUNT(DISTINCT confluence_space_key) as unique_spaces,
                    AVG(retry_count) as avg_retry_count
                FROM confluence_publications
            """)
            
            overall_stats = dict(cursor.fetchone())
            
            # Статистика по пространствам
            cursor.execute("""
                SELECT
                    confluence_space_key,
                    COUNT(*) as publications_count,
                    SUM(CASE WHEN publication_status = 'published' THEN 1 ELSE 0 END) as published_count
                FROM confluence_publications
                GROUP BY confluence_space_key
                ORDER BY publications_count DESC
            """)
            
            space_stats = [dict(row) for row in cursor.fetchall()]
            
            # Статистика по дням (последние 30 дней)
            cursor.execute("""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as publications_count,
                    SUM(CASE WHEN publication_status = 'published' THEN 1 ELSE 0 END) as published_count
                FROM confluence_publications
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            
            daily_stats = [dict(row) for row in cursor.fetchall()]
            
            return {
                'overall': overall_stats,
                'by_space': space_stats,
                'daily': daily_stats
            }
    
    # Утилиты
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """
        Создает резервную копию базы данных
        
        Args:
            backup_path: Путь для резервной копии (опционально)
            
        Returns:
            Путь к созданной резервной копии
        """
        if not backup_path:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.db_path}.backup_{timestamp}"
        
        with self._get_connection() as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        logger.info(f"Создана резервная копия базы данных: {backup_path}")
        return backup_path
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Получает информацию о базе данных
        
        Returns:
            Информация о базе данных
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Размер базы данных
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            # Количество записей в таблицах
            cursor.execute("SELECT COUNT(*) FROM users")
            users_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM jobs")
            jobs_count = cursor.fetchone()[0]
            
            return {
                'db_path': self.db_path,
                'db_size_bytes': db_size,
                'db_size_mb': round(db_size / (1024 * 1024), 2),
                'users_count': users_count,
                'jobs_count': jobs_count,
                'backup_enabled': self.backup_enabled
            }
    
    def close(self):
        """Закрывает соединения с базой данных"""
        # В текущей реализации соединения создаются и закрываются автоматически
        # Этот метод добавлен для совместимости с тестами
        pass
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Получает всех пользователей"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Получает все задачи"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_all_confluence_publications(self) -> List[Dict[str, Any]]:
        """Получает все публикации Confluence"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM confluence_publications ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_job_confluence_publications(self, job_id: str) -> List[Dict[str, Any]]:
        """Получает публикации Confluence для задачи"""
        return self.get_confluence_publications_by_job_id(job_id)
    
    def update_job_status(self, job_id: str, status: str, progress: int, message: str = None):
        """Обновляет статус задачи"""
        update_data = {
            'status': status,
            'progress': progress
        }
        if message:
            update_data['message'] = message
        
        return self.update_job(job_id, update_data)
    
    def update_confluence_publication_status(self, publication_id: int, status: str, page_url: str = None):
        """Обновляет статус публикации Confluence"""
        update_data = {
            'publication_status': status
        }
        if page_url:
            update_data['confluence_page_url'] = page_url
        
        return self.update_confluence_publication(publication_id, update_data)

def create_database_manager(config: Dict[str, Any]) -> DatabaseManager:
    """
    Создает экземпляр DatabaseManager
    
    Args:
        config: Конфигурация приложения
        
    Returns:
        Настроенный экземпляр DatabaseManager
    """
    db_config = config.get('database', {
        'type': 'sqlite',
        'path': 'meeting_processor.db',
        'backup_enabled': True,
        'backup_interval_hours': 24
    })
    
    return DatabaseManager(db_config)