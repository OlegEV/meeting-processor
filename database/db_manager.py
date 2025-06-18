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

from .models import User, Job, DatabaseSchema, DatabaseValidator

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
            
            # Создаем таблицы
            self._create_tables()
            
            # Создаем индексы
            self._create_indexes()
            
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