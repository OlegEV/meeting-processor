#!/usr/bin/env python3
"""
Скрипт для отладки JWT токенов
"""

import jwt
import json
from datetime import datetime, timedelta
import time

def create_debug_token():
    """Создает отладочный JWT токен"""
    now = datetime.utcnow()
    payload = {
        'sub': 'debug_user',
        'email': 'debug@example.com',
        'name': 'Debug User',
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=1)).timestamp()),
    }
    
    print("Создание токена:")
    print(f"Текущее время: {now}")
    print(f"Время создания (iat): {payload['iat']} ({datetime.fromtimestamp(payload['iat'])})")
    print(f"Время истечения (exp): {payload['exp']} ({datetime.fromtimestamp(payload['exp'])})")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    token = jwt.encode(payload, key='', algorithm='none')
    print(f"Созданный токен: {token}")
    
    return token

def decode_debug_token(token):
    """Декодирует JWT токен для отладки"""
    print("\nДекодирование токена:")
    
    try:
        # Декодируем без проверки
        decoded_unverified = jwt.decode(token, options={"verify_signature": False})
        print(f"Декодированный payload (без проверки): {json.dumps(decoded_unverified, indent=2)}")
        
        # Проверяем срок действия
        exp = decoded_unverified.get('exp')
        if exp:
            exp_time = datetime.fromtimestamp(exp)
            current_time = datetime.utcnow()
            print(f"Время истечения: {exp_time}")
            print(f"Текущее время: {current_time}")
            print(f"Токен истек: {current_time > exp_time}")
        
        # Декодируем с проверкой срока действия
        try:
            decoded_verified = jwt.decode(
                token, 
                key='', 
                algorithms=['none'],
                options={
                    "verify_signature": False,
                    "verify_exp": True,
                    "verify_aud": False,
                    "verify_iss": False,
                    "verify_nbf": True,
                    "verify_iat": True,
                }
            )
            print("✅ Токен прошел валидацию с проверкой срока действия")
            return decoded_verified
        except jwt.ExpiredSignatureError:
            print("❌ Токен истек")
            return None
        except jwt.InvalidTokenError as e:
            print(f"❌ Невалидный токен: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка декодирования: {e}")
        return None

def test_jwt_validation():
    """Тестирует валидацию JWT"""
    print("🧪 Тестирование JWT валидации")
    print("=" * 40)
    
    # Создаем токен
    token = create_debug_token()
    
    # Декодируем токен
    decoded = decode_debug_token(token)
    
    if decoded:
        print("✅ Токен успешно создан и декодирован")
    else:
        print("❌ Проблема с токеном")
    
    # Тестируем с истекшим токеном
    print("\n" + "=" * 40)
    print("Тестирование истекшего токена:")
    
    past_time = datetime.utcnow() - timedelta(hours=1)
    expired_payload = {
        'sub': 'expired_user',
        'iat': int(past_time.timestamp()),
        'exp': int((past_time + timedelta(minutes=30)).timestamp()),
    }
    
    expired_token = jwt.encode(expired_payload, key='', algorithm='none')
    print(f"Истекший токен: {expired_token}")
    
    decoded_expired = decode_debug_token(expired_token)
    if not decoded_expired:
        print("✅ Истекший токен корректно отклонен")
    else:
        print("❌ Истекший токен принят (ошибка)")

if __name__ == "__main__":
    test_jwt_validation()