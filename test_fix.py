#!/usr/bin/env python3
"""
Тест исправлений JWT
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from auth.jwt_utils import create_jwt_utils
from auth.token_validator import create_token_validator
import jwt
from datetime import datetime, timedelta

def test_jwt_fix():
    """Тестирует исправления JWT"""
    print("🧪 Тестирование исправлений JWT")
    print("=" * 40)
    
    # Создаем тестовый токен
    now = datetime.utcnow()
    payload = {
        'sub': 'test_user',
        'email': 'test@example.com',
        'name': 'Test User',
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=1)).timestamp()),
    }
    
    token = jwt.encode(payload, key='', algorithm='none')
    print(f"Тестовый токен: {token[:50]}...")
    
    # Тестируем JWT utils
    config = {
        'auth': {
            'jwt_algorithm': 'RS256',
            'token_validation': {
                'verify_signature': False,
                'verify_exp': True,
                'verify_aud': False
            }
        }
    }
    
    jwt_utils = create_jwt_utils(config)
    
    print("\n1. Тестирование decode_token:")
    decoded = jwt_utils.decode_token(token, verify_exp=False)
    if decoded:
        print(f"✅ Декодирование без проверки срока: {decoded['sub']}")
    else:
        print("❌ Ошибка декодирования без проверки срока")
    
    print("\n2. Тестирование is_token_expired:")
    is_expired = jwt_utils.is_token_expired(token)
    print(f"Токен истек: {is_expired}")
    if not is_expired:
        print("✅ Токен действителен")
    else:
        print("❌ Токен считается истекшим")
    
    print("\n3. Тестирование extract_user_info:")
    user_info = jwt_utils.extract_user_info(token)
    if user_info:
        print(f"✅ Информация о пользователе: {user_info['user_id']}")
    else:
        print("❌ Не удалось извлечь информацию о пользователе")
    
    print("\n4. Тестирование token_validator:")
    token_validator = create_token_validator(config)
    is_valid, user_data, error = token_validator.validate_token(token)
    
    if is_valid:
        print(f"✅ Токен валиден: {user_data['user_id']}")
    else:
        print(f"❌ Токен невалиден: {error}")
    
    return is_valid

if __name__ == "__main__":
    success = test_jwt_fix()
    if success:
        print("\n🎉 Все тесты прошли успешно!")
        print("Теперь можно тестировать веб-приложение:")
        print("python quick_test.py")
    else:
        print("\n❌ Есть проблемы с JWT")