#!/usr/bin/env python3
"""
Менеджер пользователей для работы с пользовательскими данными
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class UserManager:
    """Менеджер для работы с пользователями"""
    
    def __init__(self, db_manager=None):
        """
        Инициализация менеджера пользователей
        
        Args:
            db_manager: Менеджер базы данных (будет установлен позже)
        """
        self.db_manager = db_manager
    
    def set_db_manager(self, db_manager):
        """
        Устанавливает менеджер базы данных
        
        Args:
            db_manager: Менеджер базы данных
        """
        self.db_manager = db_manager
    
    def ensure_user_exists(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обеспечивает существование пользователя в базе данных
        Создает пользователя если его нет, обновляет информацию если есть
        
        Args:
            user_info: Информация о пользователе из JWT токена
            
        Returns:
            Информация о пользователе из базы данных
        """
        if not self.db_manager:
            logger.warning("DB manager не установлен, возвращаем информацию из токена")
            return user_info
            
        user_id = user_info.get('user_id')
        if not user_id:
            raise ValueError("user_info должен содержать user_id")
        
        try:
            # Проверяем, существует ли пользователь
            existing_user = self.db_manager.get_user_by_id(user_id)
            
            if existing_user:
                # Обновляем время последнего входа
                self.db_manager.update_user_last_login(user_id)
                
                # Обновляем информацию о пользователе если она изменилась
                updated_info = self._extract_user_data_for_db(user_info)
                if self._should_update_user_info(existing_user, updated_info):
                    self.db_manager.update_user_info(user_id, updated_info)
                    logger.info(f"Обновлена информация о пользователе: {user_id}")
                
                return existing_user
            else:
                # Создаем нового пользователя
                user_data = self._extract_user_data_for_db(user_info)
                created_user = self.db_manager.create_user(user_data)
                logger.info(f"Создан новый пользователь: {user_id}")
                return created_user
                
        except Exception as e:
            logger.error(f"Ошибка при работе с пользователем {user_id}: {e}")
            # В случае ошибки возвращаем информацию из токена
            return user_info
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по идентификатору
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Информация о пользователе или None если не найден
        """
        if not self.db_manager:
            return None
            
        try:
            return self.db_manager.get_user_by_id(user_id)
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {user_id}: {e}")
            return None
    
    def update_user_last_login(self, user_id: str) -> bool:
        """
        Обновляет время последнего входа пользователя
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            True если обновление успешно, False иначе
        """
        if not self.db_manager:
            return False
            
        try:
            self.db_manager.update_user_last_login(user_id)
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления времени входа для пользователя {user_id}: {e}")
            return False
    
    def _extract_user_data_for_db(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает данные пользователя для сохранения в базе данных
        
        Args:
            user_info: Информация о пользователе из JWT токена
            
        Returns:
            Данные для сохранения в базе данных
        """
        return {
            'user_id': user_info.get('user_id'),
            'email': user_info.get('email'),
            'name': (user_info.get('name') or 
                    user_info.get('given_name') or 
                    user_info.get('preferred_username')),
            'full_name': user_info.get('name'),
            'given_name': user_info.get('given_name'),
            'family_name': user_info.get('family_name'),
            'preferred_username': user_info.get('preferred_username')
        }
    
    def _should_update_user_info(self, existing_user: Dict[str, Any], new_info: Dict[str, Any]) -> bool:
        """
        Определяет, нужно ли обновлять информацию о пользователе
        
        Args:
            existing_user: Существующая информация о пользователе
            new_info: Новая информация о пользователе
            
        Returns:
            True если нужно обновить, False иначе
        """
        # Поля для сравнения
        fields_to_compare = ['email', 'name', 'full_name', 'given_name', 'family_name', 'preferred_username']
        
        for field in fields_to_compare:
            existing_value = existing_user.get(field)
            new_value = new_info.get(field)
            
            # Если новое значение не пустое и отличается от существующего
            if new_value and new_value != existing_value:
                return True
        
        return False
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Получает статистику пользователя
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Статистика пользователя
        """
        if not self.db_manager:
            return {}
            
        try:
            stats = {
                'total_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'processing_jobs': 0,
                'first_job_date': None,
                'last_job_date': None
            }
            
            # Получаем статистику задач пользователя
            job_stats = self.db_manager.get_user_job_stats(user_id)
            if job_stats:
                stats.update(job_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователя {user_id}: {e}")
            return {}
    
    def cleanup_user_data(self, user_id: str, days_old: int = 30) -> bool:
        """
        Очищает старые данные пользователя
        
        Args:
            user_id: Идентификатор пользователя
            days_old: Возраст данных в днях для удаления
            
        Returns:
            True если очистка успешна, False иначе
        """
        if not self.db_manager:
            return False
            
        try:
            # Удаляем старые завершенные задачи
            deleted_count = self.db_manager.cleanup_old_jobs(user_id, days_old)
            if deleted_count > 0:
                logger.info(f"Удалено {deleted_count} старых задач для пользователя {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка очистки данных пользователя {user_id}: {e}")
            return False
    
    def validate_user_access(self, user_id: str, resource_user_id: str) -> bool:
        """
        Проверяет, имеет ли пользователь доступ к ресурсу
        
        Args:
            user_id: Идентификатор текущего пользователя
            resource_user_id: Идентификатор пользователя-владельца ресурса
            
        Returns:
            True если доступ разрешен, False иначе
        """
        # Простая проверка - пользователь может доступиться только к своим ресурсам
        return user_id == resource_user_id
    
    def get_user_display_name(self, user_info: Dict[str, Any]) -> str:
        """
        Получает отображаемое имя пользователя
        
        Args:
            user_info: Информация о пользователе
            
        Returns:
            Отображаемое имя пользователя
        """
        # Пробуем разные поля для имени в порядке приоритета
        name = (user_info.get('name') or 
                user_info.get('given_name') or 
                user_info.get('preferred_username'))
        
        if name:
            return name
            
        # Если имени нет, используем email без домена
        email = user_info.get('email')
        if email and '@' in email:
            return email.split('@')[0]
            
        # В крайнем случае используем user_id
        return user_info.get('user_id', 'Unknown User')

def create_user_manager(db_manager=None) -> UserManager:
    """
    Создает экземпляр UserManager
    
    Args:
        db_manager: Менеджер базы данных (опционально)
        
    Returns:
        Настроенный экземпляр UserManager
    """
    return UserManager(db_manager)