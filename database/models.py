#!/usr/bin/env python3
"""
Модели базы данных для системы обработки встреч
"""

import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class User:
    """Модель пользователя"""
    
    def __init__(self, user_id: str, email: Optional[str] = None, name: Optional[str] = None,
                 created_at: Optional[datetime] = None, last_login: Optional[datetime] = None,
                 **kwargs):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login
        
        # Дополнительные поля
        self.full_name = kwargs.get('full_name')
        self.given_name = kwargs.get('given_name')
        self.family_name = kwargs.get('family_name')
        self.preferred_username = kwargs.get('preferred_username')
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'name': self.name,
            'full_name': self.full_name,
            'given_name': self.given_name,
            'family_name': self.family_name,
            'preferred_username': self.preferred_username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Создает объект из словаря"""
        created_at = None
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.utcnow()
        
        last_login = None
        if data.get('last_login'):
            try:
                last_login = datetime.fromisoformat(data['last_login'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        return cls(
            user_id=data['user_id'],
            email=data.get('email'),
            name=data.get('name'),
            created_at=created_at,
            last_login=last_login,
            full_name=data.get('full_name'),
            given_name=data.get('given_name'),
            family_name=data.get('family_name'),
            preferred_username=data.get('preferred_username')
        )

class Job:
    """Модель задачи обработки"""
    
    def __init__(self, job_id: str, user_id: str, filename: str, template: str,
                 status: str = 'uploaded', progress: int = 0, message: str = '',
                 file_path: Optional[str] = None, transcript_file: Optional[str] = None,
                 summary_file: Optional[str] = None, created_at: Optional[datetime] = None,
                 completed_at: Optional[datetime] = None, error: Optional[str] = None,
                 **kwargs):
        self.job_id = job_id
        self.user_id = user_id
        self.filename = filename
        self.template = template
        self.status = status
        self.progress = progress
        self.message = message
        self.file_path = file_path
        self.transcript_file = transcript_file
        self.summary_file = summary_file
        self.created_at = created_at or datetime.utcnow()
        self.completed_at = completed_at
        self.error = error
        
        # Дополнительные поля
        self.original_job_id = kwargs.get('original_job_id')
        self.metadata = kwargs.get('metadata', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            'job_id': self.job_id,
            'user_id': self.user_id,
            'filename': self.filename,
            'template': self.template,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'file_path': self.file_path,
            'transcript_file': self.transcript_file,
            'summary_file': self.summary_file,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
            'original_job_id': self.original_job_id,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Создает объект из словаря"""
        created_at = None
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.utcnow()
        
        completed_at = None
        if data.get('completed_at'):
            try:
                completed_at = datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Парсим metadata если это строка JSON
        metadata = data.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        
        return cls(
            job_id=data['job_id'],
            user_id=data['user_id'],
            filename=data['filename'],
            template=data['template'],
            status=data.get('status', 'uploaded'),
            progress=data.get('progress', 0),
            message=data.get('message', ''),
            file_path=data.get('file_path'),
            transcript_file=data.get('transcript_file'),
            summary_file=data.get('summary_file'),
            created_at=created_at,
            completed_at=completed_at,
            error=data.get('error'),
            original_job_id=data.get('original_job_id'),
            metadata=metadata
        )
    
    def is_completed(self) -> bool:
        """Проверяет, завершена ли задача"""
        return self.status == 'completed'
    
    def is_failed(self) -> bool:
        """Проверяет, завершилась ли задача с ошибкой"""
        return self.status == 'error'
    
    def is_processing(self) -> bool:
        """Проверяет, обрабатывается ли задача"""
        return self.status in ['uploaded', 'processing']

class DatabaseSchema:
    """Схема базы данных"""
    
    @staticmethod
    def get_create_tables_sql() -> List[str]:
        """Возвращает SQL для создания таблиц"""
        return [
            # Таблица пользователей
            """
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
            )
            """,
            
            # Таблица задач
            """
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
            )
            """
        ]
    
    @staticmethod
    def get_create_indexes_sql() -> List[str]:
        """Возвращает SQL для создания индексов"""
        return [
            "CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON jobs (user_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)",
            "CREATE INDEX IF NOT EXISTS idx_users_last_login ON users (last_login)"
        ]
    
    @staticmethod
    def get_migration_sql(version: int) -> List[str]:
        """Возвращает SQL для миграции определенной версии"""
        migrations = {
            1: DatabaseSchema.get_create_tables_sql(),
            2: DatabaseSchema.get_create_indexes_sql()
        }
        return migrations.get(version, [])

class DatabaseValidator:
    """Валидатор данных для базы данных"""
    
    @staticmethod
    def validate_user_data(data: Dict[str, Any]) -> bool:
        """Валидирует данные пользователя"""
        if not data.get('user_id'):
            return False
        
        user_id = data['user_id']
        if not isinstance(user_id, str) or len(user_id.strip()) == 0:
            return False
        
        # Проверяем email если указан
        email = data.get('email')
        if email and not isinstance(email, str):
            return False
        
        return True
    
    @staticmethod
    def validate_job_data(data: Dict[str, Any]) -> bool:
        """Валидирует данные задачи"""
        required_fields = ['job_id', 'user_id', 'filename', 'template']
        
        for field in required_fields:
            if not data.get(field):
                return False
            if not isinstance(data[field], str) or len(data[field].strip()) == 0:
                return False
        
        # Проверяем статус
        status = data.get('status', 'uploaded')
        valid_statuses = ['uploaded', 'processing', 'completed', 'error']
        if status not in valid_statuses:
            return False
        
        # Проверяем прогресс
        progress = data.get('progress', 0)
        if not isinstance(progress, int) or progress < 0 or progress > 100:
            return False
        
        return True
    
    @staticmethod
    def sanitize_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Очищает данные пользователя"""
        sanitized = {}
        
        # Обязательные поля
        sanitized['user_id'] = str(data['user_id']).strip()
        
        # Опциональные поля
        for field in ['email', 'name', 'full_name', 'given_name', 'family_name', 'preferred_username']:
            value = data.get(field)
            if value:
                sanitized[field] = str(value).strip()
        
        return sanitized
    
    @staticmethod
    def sanitize_job_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Очищает данные задачи"""
        sanitized = {}
        
        # Обязательные поля
        for field in ['job_id', 'user_id', 'filename', 'template']:
            sanitized[field] = str(data[field]).strip()
        
        # Статус и прогресс
        sanitized['status'] = data.get('status', 'uploaded')
        sanitized['progress'] = max(0, min(100, int(data.get('progress', 0))))
        
        # Опциональные поля
        for field in ['message', 'file_path', 'transcript_file', 'summary_file', 'error', 'original_job_id']:
            value = data.get(field)
            if value:
                sanitized[field] = str(value).strip()
        
        # Metadata
        metadata = data.get('metadata', {})
        if isinstance(metadata, dict):
            sanitized['metadata'] = json.dumps(metadata)
        elif isinstance(metadata, str):
            sanitized['metadata'] = metadata
        else:
            sanitized['metadata'] = '{}'
        
        return sanitized