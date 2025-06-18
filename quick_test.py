#!/usr/bin/env python3
"""
Быстрый тест аутентификации
"""

import requests
import jwt
from datetime import datetime, timedelta

def create_simple_token():
    """Создает простой тестовый токен"""
    now = datetime.utcnow()
    payload = {
        'sub': 'test_user',
        'email': 'test@example.com',
        'name': 'Test User',
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=1)).timestamp()),
    }
    
    token = jwt.encode(payload, key='', algorithm='none')
    return token

def test_single_request():
    """Тестирует один запрос с токеном"""
    token = create_simple_token()
    
    print(f"Тестовый токен: {token}")
    print(f"Длина токена: {len(token)}")
    
    # Декодируем токен для проверки
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        print(f"Декодированный токен: {decoded}")
        
        exp_time = datetime.fromtimestamp(decoded['exp'])
        current_time = datetime.utcnow()
        print(f"Время истечения: {exp_time}")
        print(f"Текущее время: {current_time}")
        print(f"Токен действителен: {current_time < exp_time}")
        
    except Exception as e:
        print(f"Ошибка декодирования: {e}")
        return
    
    # Тестируем запрос
    headers = {'X-Identity-Token': token}
    
    try:
        print("\nТестирование запроса к /...")
        response = requests.get('http://localhost:5000/', headers=headers, timeout=10)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Успешно!")
        else:
            print(f"❌ Ошибка: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удается подключиться к серверу. Убедитесь, что веб-приложение запущено.")
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")

if __name__ == "__main__":
    test_single_request()