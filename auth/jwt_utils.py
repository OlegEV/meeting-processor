#!/usr/bin/env python3
"""
Утилиты для работы с JWT токенами
"""

import jwt
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class JWTUtils:
    """Утилиты для работы с JWT токенами"""
    
    def __init__(self, algorithm: str = "RS256", verify_signature: bool = False):
        """
        Инициализация JWT утилит
        
        Args:
            algorithm: Алгоритм JWT (по умолчанию RS256)
            verify_signature: Проверять ли подпись (False для доверия reverse proxy)
        """
        self.algorithm = algorithm
        self.verify_signature = verify_signature
        
    def decode_token(self, token: str, verify_exp: bool = True, verify_aud: bool = False) -> Optional[Dict[str, Any]]:
        """
        Декодирует JWT токен
        
        Args:
            token: JWT токен для декодирования
            verify_exp: Проверять ли срок действия токена
            verify_aud: Проверять ли аудиторию токена
            
        Returns:
            Словарь с claims токена или None в случае ошибки
        """
        try:
            
            # Настройки верификации
            options = {
                "verify_signature": self.verify_signature,
                "verify_exp": verify_exp,
                "verify_aud": verify_aud,
                "verify_iss": False,  # Не проверяем издателя
                "verify_nbf": False,   # Отключаем проверку "not before" для тестирования
                "verify_iat": False,   # Отключаем проверку "issued at" для тестирования
            }
            
            
            # Декодируем токен без проверки подписи (доверяем reverse proxy)
            if not self.verify_signature:
                decoded = jwt.decode(
                    token,
                    key="",  # Пустой ключ для алгоритма none
                    algorithms=["none"],  # Явно указываем алгоритм none
                    options=options
                )
            else:
                # Если нужна проверка подписи, потребуется публичный ключ
                raise NotImplementedError("Проверка подписи требует настройки публичного ключа")
            
            return decoded
            
        except jwt.ExpiredSignatureError as e:
            logger.warning(f"Токен истек: {e}")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Невалидный токен: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка декодирования токена: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def extract_user_id(self, token: str) -> Optional[str]:
        """
        Извлекает идентификатор пользователя из токена
        
        Args:
            token: JWT токен
            
        Returns:
            Идентификатор пользователя из claim 'sub' или None
        """
        decoded = self.decode_token(token)
        if not decoded:
            return None
            
        user_id = decoded.get('sub')
        if not user_id:
            logger.warning("Токен не содержит claim 'sub'")
            return None
            
        if not isinstance(user_id, str) or not user_id.strip():
            logger.warning(f"Невалидный user_id в токене: {user_id}")
            return None
            
        return user_id.strip()
    
    def extract_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Извлекает информацию о пользователе из токена
        
        Args:
            token: JWT токен
            
        Returns:
            Словарь с информацией о пользователе или None
        """
        # Декодируем без проверки срока действия для извлечения информации
        decoded = self.decode_token(token, verify_exp=False)
        if not decoded:
            return None
            
        user_id = decoded.get('sub')
        if not user_id:
            return None
            
        # Извлекаем дополнительную информацию о пользователе
        user_info = {
            'user_id': user_id,
            'email': decoded.get('email'),
            'name': decoded.get('name') or decoded.get('given_name'),
            'full_name': decoded.get('name'),
            'given_name': decoded.get('given_name'),
            'family_name': decoded.get('family_name'),
            'preferred_username': decoded.get('preferred_username'),
            'exp': decoded.get('exp'),
            'iat': decoded.get('iat'),
            'iss': decoded.get('iss'),
            'aud': decoded.get('aud')
        }
        
        # Удаляем None значения
        user_info = {k: v for k, v in user_info.items() if v is not None}
        
        return user_info
    
    def is_token_expired(self, token: str) -> bool:
        """
        Проверяет, истек ли токен
        
        Args:
            token: JWT токен
            
        Returns:
            True если токен истек, False если действителен
        """
        try:
            # Декодируем токен без проверки срока действия
            decoded = self.decode_token(token, verify_exp=False)
            if not decoded:
                return True
                
            exp = decoded.get('exp')
            if not exp:
                # Если нет срока действия, считаем токен действительным
                return False
                
            current_time = datetime.utcnow().timestamp()
            is_expired = current_time > exp
            
            return is_expired
            
        except Exception as e:
            logger.error(f"Ошибка проверки срока действия токена: {e}")
            return True
    
    def validate_token_format(self, token: str) -> bool:
        """
        Проверяет формат JWT токена
        
        Args:
            token: Строка токена
            
        Returns:
            True если формат корректный, False иначе
        """
        if not token or not isinstance(token, str):
            return False
            
        # JWT токен должен состоять из 3 частей, разделенных точками
        parts = token.split('.')
        if len(parts) != 3:
            return False
            
        # Каждая часть должна быть base64url encoded
        try:
            for part in parts:
                # Добавляем padding если нужно
                padded = part + '=' * (4 - len(part) % 4)
                jwt.utils.base64url_decode(padded)
            return True
        except Exception:
            return False

def create_jwt_utils(config: Dict[str, Any]) -> JWTUtils:
    """
    Создает экземпляр JWTUtils на основе конфигурации
    
    Args:
        config: Конфигурация аутентификации
        
    Returns:
        Настроенный экземпляр JWTUtils
    """
    auth_config = config.get('auth', {})
    token_validation = auth_config.get('token_validation', {})
    
    return JWTUtils(
        algorithm=auth_config.get('jwt_algorithm', 'RS256'),
        verify_signature=token_validation.get('verify_signature', False)
    )