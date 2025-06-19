#!/usr/bin/env python3
"""
Модуль аутентификации и авторизации для веб-приложения
"""

from .jwt_utils import JWTUtils, create_jwt_utils
from .token_validator import TokenValidator, TokenValidationError, create_token_validator
from .user_context import (
    UserContext, 
    UserContextManager, 
    get_current_user_id, 
    get_current_user, 
    require_user_id, 
    is_authenticated,
    with_user_context
)
from .decorators import (
    AuthDecorators,
    init_auth_decorators,
    require_auth,
    require_user_context,
    optional_auth,
    create_auth_middleware,
    create_auth_teardown
)
from .user_manager import UserManager, create_user_manager

__all__ = [
    # JWT утилиты
    'JWTUtils',
    'create_jwt_utils',
    
    # Валидация токенов
    'TokenValidator',
    'TokenValidationError',
    'create_token_validator',
    
    # Контекст пользователя
    'UserContext',
    'UserContextManager',
    'get_current_user_id',
    'get_current_user',
    'require_user_id',
    'is_authenticated',
    'with_user_context',
    
    # Декораторы
    'AuthDecorators',
    'init_auth_decorators',
    'require_auth',
    'require_user_context',
    'optional_auth',
    'create_auth_middleware',
    'create_auth_teardown',
    
    # Менеджер пользователей
    'UserManager',
    'create_user_manager'
]

def create_auth_system(config):
    """
    Создает полную систему аутентификации
    
    Args:
        config: Конфигурация приложения
        
    Returns:
        Кортеж (token_validator, user_manager, auth_middleware, auth_teardown)
    """
    # Создаем компоненты
    token_validator = create_token_validator(config)
    user_manager = create_user_manager()
    
    # Инициализируем глобальные декораторы с конфигурацией
    init_auth_decorators(token_validator, config)
    
    # Создаем middleware и teardown с конфигурацией
    auth_middleware = create_auth_middleware(token_validator, config)
    auth_teardown = create_auth_teardown()
    
    return token_validator, user_manager, auth_middleware, auth_teardown