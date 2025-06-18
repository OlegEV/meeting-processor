#!/usr/bin/env python3
"""
Валидатор JWT токенов для аутентификации пользователей
"""

import logging
from typing import Optional, Dict, Any, Tuple
from flask import request

from .jwt_utils import JWTUtils

logger = logging.getLogger(__name__)

class TokenValidator:
    """Валидатор JWT токенов"""
    
    def __init__(self, jwt_utils: JWTUtils, token_header: str = "X-Identity-Token"):
        """
        Инициализация валидатора токенов
        
        Args:
            jwt_utils: Утилиты для работы с JWT
            token_header: Имя HTTP заголовка с токеном
        """
        self.jwt_utils = jwt_utils
        self.token_header = token_header
        
    def extract_token_from_request(self, request_obj=None) -> Optional[str]:
        """
        Извлекает токен из HTTP запроса
        
        Args:
            request_obj: Объект запроса Flask (по умолчанию текущий request)
            
        Returns:
            JWT токен или None если не найден
        """
        if request_obj is None:
            request_obj = request
            
        # Извлекаем токен из заголовка
        token = request_obj.headers.get(self.token_header)
        
        if not token:
            logger.debug(f"Токен не найден в заголовке {self.token_header}")
            return None
            
        # Убираем префикс Bearer если есть
        if token.startswith('Bearer '):
            token = token[7:]
        elif token.startswith('bearer '):
            token = token[7:]
            
        token = token.strip()
        
        if not token:
            logger.debug("Пустой токен после обработки")
            return None
            
        return token
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Валидирует JWT токен
        
        Args:
            token: JWT токен для валидации
            
        Returns:
            Кортеж (is_valid, user_info, error_message)
        """
        if not token:
            return False, None, "Токен не предоставлен"
            
        # Проверяем формат токена
        if not self.jwt_utils.validate_token_format(token):
            return False, None, "Неверный формат токена"
            
        # Проверяем, не истек ли токен
        is_expired = self.jwt_utils.is_token_expired(token)
        logger.debug(f"Проверка срока действия токена: истек={is_expired}")
        if is_expired:
            return False, None, "Токен истек"
            
        # Извлекаем информацию о пользователе
        user_info = self.jwt_utils.extract_user_info(token)
        logger.debug(f"Извлеченная информация о пользователе: {user_info}")
        if not user_info:
            return False, None, "Не удалось извлечь информацию о пользователе из токена"
            
        # Проверяем наличие обязательного поля user_id
        if not user_info.get('user_id'):
            return False, None, "Токен не содержит идентификатор пользователя"
            
        logger.debug(f"Токен валиден для пользователя: {user_info['user_id']}")
        return True, user_info, None
    
    def validate_request(self, request_obj=None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Валидирует токен из HTTP запроса
        
        Args:
            request_obj: Объект запроса Flask (по умолчанию текущий request)
            
        Returns:
            Кортеж (is_valid, user_info, error_message)
        """
        # Извлекаем токен из запроса
        token = self.extract_token_from_request(request_obj)
        if not token:
            return False, None, f"Токен не найден в заголовке {self.token_header}"
            
        # Валидируем токен
        return self.validate_token(token)
    
    def get_user_id_from_request(self, request_obj=None) -> Optional[str]:
        """
        Извлекает идентификатор пользователя из запроса
        
        Args:
            request_obj: Объект запроса Flask (по умолчанию текущий request)
            
        Returns:
            Идентификатор пользователя или None
        """
        is_valid, user_info, error = self.validate_request(request_obj)
        if not is_valid or not user_info:
            return None
            
        return user_info.get('user_id')
    
    def get_user_info_from_request(self, request_obj=None) -> Optional[Dict[str, Any]]:
        """
        Извлекает информацию о пользователе из запроса
        
        Args:
            request_obj: Объект запроса Flask (по умолчанию текущий request)
            
        Returns:
            Информация о пользователе или None
        """
        is_valid, user_info, error = self.validate_request(request_obj)
        if not is_valid or not user_info:
            return None
            
        return user_info

class TokenValidationError(Exception):
    """Исключение для ошибок валидации токена"""
    
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def create_token_validator(config: Dict[str, Any]) -> TokenValidator:
    """
    Создает экземпляр TokenValidator на основе конфигурации
    
    Args:
        config: Конфигурация приложения
        
    Returns:
        Настроенный экземпляр TokenValidator
    """
    from .jwt_utils import create_jwt_utils
    
    auth_config = config.get('auth', {})
    jwt_utils = create_jwt_utils(config)
    token_header = auth_config.get('token_header', 'X-Identity-Token')
    
    return TokenValidator(jwt_utils, token_header)