#!/usr/bin/env python3
"""
Контекст пользователя для хранения информации о текущем аутентифицированном пользователе
"""

import threading
from typing import Optional, Dict, Any
from contextvars import ContextVar
import logging

logger = logging.getLogger(__name__)

# Context variable для хранения информации о пользователе
_user_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('user_context', default=None)

class UserContext:
    """Контекст текущего пользователя"""
    
    @staticmethod
    def set_current_user(user_info: Dict[str, Any]) -> None:
        """
        Устанавливает информацию о текущем пользователе
        
        Args:
            user_info: Информация о пользователе из JWT токена
        """
        if not user_info or not user_info.get('user_id'):
            raise ValueError("user_info должен содержать user_id")
            
        _user_context.set(user_info)
    
    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """
        Получает информацию о текущем пользователе
        
        Returns:
            Информация о пользователе или None если не установлена
        """
        return _user_context.get()
    
    @staticmethod
    def get_current_user_id() -> Optional[str]:
        """
        Получает идентификатор текущего пользователя
        
        Returns:
            Идентификатор пользователя или None если не установлен
        """
        user_info = _user_context.get()
        return user_info.get('user_id') if user_info else None
    
    @staticmethod
    def get_current_user_email() -> Optional[str]:
        """
        Получает email текущего пользователя
        
        Returns:
            Email пользователя или None если не установлен
        """
        user_info = _user_context.get()
        return user_info.get('email') if user_info else None
    
    @staticmethod
    def get_current_user_name() -> Optional[str]:
        """
        Получает имя текущего пользователя
        
        Returns:
            Имя пользователя или None если не установлено
        """
        user_info = _user_context.get()
        if not user_info:
            return None
            
        # Пробуем разные поля для имени
        return (user_info.get('name') or 
                user_info.get('given_name') or 
                user_info.get('preferred_username') or
                user_info.get('email', '').split('@')[0] if user_info.get('email') else None)
    
    @staticmethod
    def clear_current_user() -> None:
        """Очищает контекст текущего пользователя"""
        _user_context.set(None)
    
    @staticmethod
    def is_authenticated() -> bool:
        """
        Проверяет, аутентифицирован ли текущий пользователь
        
        Returns:
            True если пользователь аутентифицирован, False иначе
        """
        user_info = _user_context.get()
        return user_info is not None and user_info.get('user_id') is not None
    
    @staticmethod
    def require_authentication() -> Dict[str, Any]:
        """
        Требует аутентификации и возвращает информацию о пользователе
        
        Returns:
            Информация о пользователе
            
        Raises:
            RuntimeError: Если пользователь не аутентифицирован
        """
        user_info = _user_context.get()
        if not user_info or not user_info.get('user_id'):
            raise RuntimeError("Пользователь не аутентифицирован")
        return user_info
    
    @staticmethod
    def require_user_id() -> str:
        """
        Требует аутентификации и возвращает идентификатор пользователя
        
        Returns:
            Идентификатор пользователя
            
        Raises:
            RuntimeError: Если пользователь не аутентифицирован
        """
        user_info = UserContext.require_authentication()
        return user_info['user_id']

class UserContextManager:
    """Менеджер контекста для автоматической установки и очистки пользователя"""
    
    def __init__(self, user_info: Dict[str, Any]):
        """
        Инициализация менеджера контекста
        
        Args:
            user_info: Информация о пользователе
        """
        self.user_info = user_info
        self.previous_user = None
    
    def __enter__(self):
        """Устанавливает пользователя при входе в контекст"""
        self.previous_user = UserContext.get_current_user()
        UserContext.set_current_user(self.user_info)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Восстанавливает предыдущего пользователя при выходе из контекста"""
        if self.previous_user:
            UserContext.set_current_user(self.previous_user)
        else:
            UserContext.clear_current_user()

# Вспомогательные функции для удобства использования

def get_current_user_id() -> Optional[str]:
    """
    Получает идентификатор текущего пользователя
    
    Returns:
        Идентификатор пользователя или None
    """
    return UserContext.get_current_user_id()

def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Получает информацию о текущем пользователе
    
    Returns:
        Информация о пользователе или None
    """
    return UserContext.get_current_user()

def require_user_id() -> str:
    """
    Требует аутентификации и возвращает идентификатор пользователя
    
    Returns:
        Идентификатор пользователя
        
    Raises:
        RuntimeError: Если пользователь не аутентифицирован
    """
    return UserContext.require_user_id()

def is_authenticated() -> bool:
    """
    Проверяет, аутентифицирован ли текущий пользователь
    
    Returns:
        True если пользователь аутентифицирован, False иначе
    """
    return UserContext.is_authenticated()

def with_user_context(user_info: Dict[str, Any]):
    """
    Декоратор для установки пользовательского контекста
    
    Args:
        user_info: Информация о пользователе
        
    Returns:
        Менеджер контекста
    """
    return UserContextManager(user_info)