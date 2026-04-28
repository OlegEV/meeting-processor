#!/usr/bin/env python3
"""
Декораторы для аутентификации и авторизации
"""

import logging
import os
from functools import wraps
from typing import Dict, Any, Optional, Callable
from flask import request, jsonify, redirect, url_for, flash

from .token_validator import TokenValidator, TokenValidationError
from .user_context import UserContext

logger = logging.getLogger(__name__)

# Имя переменной окружения, которой можно перекрыть auth.debug_mode из config.json.
# Удобно для локального запуска: вместо правки конфига выставляется AUTH_DEBUG_MODE=true в .env.
AUTH_DEBUG_ENV_VAR = "AUTH_DEBUG_MODE"


def _resolve_debug_mode(config_value: bool) -> bool:
    """Возвращает True, если включён отладочный режим аутентификации.

    Приоритет: переменная окружения AUTH_DEBUG_MODE > значение из config.json.
    Truthy-значения env-переменной: 1, true, yes, on (регистронезависимо).
    Любое другое значение env-переменной (включая "false"/"0") явно выключает режим.
    Если env-переменная не задана — используется значение из config.
    """
    env_value = os.getenv(AUTH_DEBUG_ENV_VAR)
    if env_value is None:
        return bool(config_value)
    return env_value.strip().lower() in ("1", "true", "yes", "on")

class AuthDecorators:
    """Класс с декораторами для аутентификации"""
    
    def __init__(self, token_validator: TokenValidator, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация декораторов
        
        Args:
            token_validator: Валидатор токенов
            config: Конфигурация приложения
        """
        self.token_validator = token_validator
        self.config = config or {}
        
        # Настройки отладочного режима
        auth_config = self.config.get('auth', {})
        self.debug_mode = _resolve_debug_mode(auth_config.get('debug_mode', False))
        self.debug_user = auth_config.get('debug_user', {
            'user_id': 'debug_user',
            'email': 'debug@localhost',
            'name': 'Debug User'
        })

        if self.debug_mode:
            source = "AUTH_DEBUG_MODE env" if os.getenv(AUTH_DEBUG_ENV_VAR) else "config.json"
            logger.warning(f"🔧 ОТЛАДОЧНЫЙ РЕЖИМ АКТИВЕН ({source}) — аутентификация отключена!")
    
    def require_auth(self, redirect_on_failure: bool = True):
        """
        Декоратор для требования аутентификации
        
        Args:
            redirect_on_failure: Перенаправлять ли на главную страницу при ошибке
            
        Returns:
            Декоратор функции
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    # Проверяем отладочный режим
                    if self.debug_mode:
                        # В отладочном режиме используем фиктивного пользователя
                        UserContext.set_current_user(self.debug_user)
                        
                        try:
                            # Вызываем оригинальную функцию
                            return f(*args, **kwargs)
                        finally:
                            # Очищаем контекст после выполнения
                            UserContext.clear_current_user()
                    
                    # Обычный режим - валидируем токен из запроса
                    is_valid, user_info, error = self.token_validator.validate_request()
                    
                    if not is_valid:
                        logger.warning(f"Неудачная аутентификация: {error}")
                        
                        # Для API запросов возвращаем JSON
                        if request.path.startswith('/api/'):
                            return jsonify({
                                'error': 'Authentication required',
                                'message': error or 'Invalid or missing authentication token'
                            }), 401
                        
                        # Для веб-интерфейса
                        if redirect_on_failure:
                            flash('Требуется аутентификация', 'error')
                            return redirect(url_for('index'))
                        else:
                            return jsonify({
                                'error': 'Authentication required',
                                'message': error or 'Invalid or missing authentication token'
                            }), 401
                    
                    # Устанавливаем контекст пользователя
                    UserContext.set_current_user(user_info)
                    
                    try:
                        # Вызываем оригинальную функцию
                        return f(*args, **kwargs)
                    finally:
                        # Очищаем контекст после выполнения
                        UserContext.clear_current_user()
                        
                except Exception as e:
                    logger.error(f"Ошибка в декораторе аутентификации: {e}")
                    
                    if request.path.startswith('/api/'):
                        return jsonify({
                            'error': 'Authentication error',
                            'message': 'Internal authentication error'
                        }), 500
                    
                    if redirect_on_failure:
                        flash('Ошибка аутентификации', 'error')
                        return redirect(url_for('index'))
                    else:
                        return jsonify({
                            'error': 'Authentication error',
                            'message': 'Internal authentication error'
                        }), 500
            
            return decorated_function
        return decorator
    
    def require_user_context(self, redirect_on_failure: bool = True):
        """
        Декоратор для требования аутентификации с установкой пользовательского контекста
        Алиас для require_auth для обратной совместимости
        
        Args:
            redirect_on_failure: Перенаправлять ли на главную страницу при ошибке
            
        Returns:
            Декоратор функции
        """
        return self.require_auth(redirect_on_failure)
    
    def optional_auth(self):
        """
        Декоратор для опциональной аутентификации
        Устанавливает контекст пользователя если токен валиден, но не требует его
        
        Returns:
            Декоратор функции
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    # Проверяем отладочный режим
                    if self.debug_mode:
                        # В отладочном режиме используем фиктивного пользователя
                        UserContext.set_current_user(self.debug_user)
                        
                        try:
                            # Вызываем оригинальную функцию
                            return f(*args, **kwargs)
                        finally:
                            # Очищаем контекст после выполнения
                            UserContext.clear_current_user()
                    
                    # Обычный режим - пытаемся валидировать токен
                    is_valid, user_info, error = self.token_validator.validate_request()
                    
                    if is_valid and user_info:
                        # Устанавливаем контекст пользователя если токен валиден
                        UserContext.set_current_user(user_info)
                    else:
                        # Очищаем контекст если токен невалиден
                        UserContext.clear_current_user()
                    
                    try:
                        # Вызываем оригинальную функцию
                        return f(*args, **kwargs)
                    finally:
                        # Очищаем контекст после выполнения
                        UserContext.clear_current_user()
                        
                except Exception as e:
                    logger.error(f"Ошибка в декораторе опциональной аутентификации: {e}")
                    # Продолжаем выполнение даже при ошибке аутентификации
                    UserContext.clear_current_user()
                    return f(*args, **kwargs)
            
            return decorated_function
        return decorator

# Глобальные декораторы для удобства использования
_auth_decorators: Optional[AuthDecorators] = None

def init_auth_decorators(token_validator: TokenValidator, config: Optional[Dict[str, Any]] = None) -> None:
    """
    Инициализирует глобальные декораторы аутентификации
    
    Args:
        token_validator: Валидатор токенов
        config: Конфигурация приложения
    """
    global _auth_decorators
    _auth_decorators = AuthDecorators(token_validator, config)

def require_auth(redirect_on_failure: bool = True):
    """
    Глобальный декоратор для требования аутентификации
    
    Args:
        redirect_on_failure: Перенаправлять ли на главную страницу при ошибке
        
    Returns:
        Декоратор функции
        
    Raises:
        RuntimeError: Если декораторы не инициализированы
    """
    if _auth_decorators is None:
        raise RuntimeError("Декораторы аутентификации не инициализированы. Вызовите init_auth_decorators()")
    
    return _auth_decorators.require_auth(redirect_on_failure)

def require_user_context(redirect_on_failure: bool = True):
    """
    Глобальный декоратор для требования аутентификации с пользовательским контекстом
    
    Args:
        redirect_on_failure: Перенаправлять ли на главную страницу при ошибке
        
    Returns:
        Декоратор функции
        
    Raises:
        RuntimeError: Если декораторы не инициализированы
    """
    if _auth_decorators is None:
        raise RuntimeError("Декораторы аутентификации не инициализированы. Вызовите init_auth_decorators()")
    
    return _auth_decorators.require_user_context(redirect_on_failure)

def optional_auth():
    """
    Глобальный декоратор для опциональной аутентификации
    
    Returns:
        Декоратор функции
        
    Raises:
        RuntimeError: Если декораторы не инициализированы
    """
    if _auth_decorators is None:
        raise RuntimeError("Декораторы аутентификации не инициализированы. Вызовите init_auth_decorators()")
    
    return _auth_decorators.optional_auth()

# Middleware функция для Flask
def create_auth_middleware(token_validator: TokenValidator, config: Optional[Dict[str, Any]] = None):
    """
    Создает middleware функцию для автоматической аутентификации
    
    Args:
        token_validator: Валидатор токенов
        config: Конфигурация приложения
        
    Returns:
        Middleware функция для Flask
    """
    config = config or {}
    auth_config = config.get('auth', {})
    debug_mode = _resolve_debug_mode(auth_config.get('debug_mode', False))
    debug_user = auth_config.get('debug_user', {
        'user_id': 'debug_user',
        'email': 'debug@localhost',
        'name': 'Debug User'
    })
    
    def auth_middleware():
        """Middleware для автоматической аутентификации на всех запросах"""
        # Пропускаем статические файлы и health check
        if (request.endpoint == 'static' or
            request.path.startswith('/static/') or
            request.path == '/health'):
            return
        
        # Проверяем отладочный режим
        if debug_mode:
            UserContext.set_current_user(debug_user)
            return
        
        # Пытаемся аутентифицировать пользователя
        try:
            is_valid, user_info, error = token_validator.validate_request()
            
            if is_valid and user_info:
                UserContext.set_current_user(user_info)
            else:
                UserContext.clear_current_user()
                    
        except Exception as e:
            logger.error(f"Ошибка в middleware аутентификации: {e}")
            UserContext.clear_current_user()
    
    return auth_middleware

def create_auth_teardown():
    """
    Создает функцию teardown для очистки контекста пользователя
    
    Returns:
        Teardown функция для Flask
    """
    def auth_teardown(exception=None):
        """Teardown для очистки контекста пользователя"""
        try:
            UserContext.clear_current_user()
        except Exception as e:
            logger.error(f"Ошибка в teardown аутентификации: {e}")
    
    return auth_teardown