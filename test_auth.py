#!/usr/bin/env python3
"""
Скрипт для тестирования системы аутентификации
"""

import json
import jwt
import time
from datetime import datetime, timedelta
import requests

def create_test_jwt(user_id: str, email: str = None, name: str = None) -> str:
    """Создает тестовый JWT токен"""
    
    # Payload токена
    now = datetime.utcnow()
    payload = {
        'sub': user_id,  # Идентификатор пользователя
        'iat': int(now.timestamp()),  # Время создания
        'exp': int((now + timedelta(hours=1)).timestamp()),  # Срок действия (через час)
    }
    
    # Добавляем дополнительную информацию если есть
    if email:
        payload['email'] = email
    if name:
        payload['name'] = name
    
    # Создаем токен без подписи (алгоритм none)
    # Это безопасно для тестирования, так как мы доверяем reverse proxy
    token = jwt.encode(payload, key='', algorithm='none')
    
    return token

def test_auth_endpoints(base_url: str = "http://localhost:5000"):
    """Тестирует endpoints с аутентификацией"""
    
    # Создаем тестовых пользователей
    test_users = [
        {
            'user_id': 'test_user_1',
            'email': 'user1@example.com',
            'name': 'Test User 1'
        },
        {
            'user_id': 'test_user_2', 
            'email': 'user2@example.com',
            'name': 'Test User 2'
        }
    ]
    
    print("🧪 Тестирование системы аутентификации")
    print("=" * 50)
    
    for user in test_users:
        print(f"\n👤 Тестирование пользователя: {user['name']} ({user['user_id']})")
        
        # Создаем токен для пользователя
        token = create_test_jwt(user['user_id'], user['email'], user['name'])
        print(f"🔑 Создан JWT токен: {token[:50]}...")
        
        # Заголовки с токеном
        headers = {
            'X-Identity-Token': token,
            'Content-Type': 'application/json'
        }
        
        # Тестируем health check
        print("\n📊 Тестирование /health")
        try:
            response = requests.get(f"{base_url}/health")
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   База данных: {data.get('database', {})}")
                print(f"   Аутентификация: {data.get('auth', {})}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # Тестируем главную страницу
        print("\n🏠 Тестирование /")
        try:
            response = requests.get(f"{base_url}/", headers=headers)
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Доступ к главной странице получен")
            else:
                print(f"   ❌ Ошибка доступа: {response.text[:100]}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # Тестируем список задач
        print("\n📋 Тестирование /jobs")
        try:
            response = requests.get(f"{base_url}/jobs", headers=headers)
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Список задач получен")
            else:
                print(f"   ❌ Ошибка: {response.text[:100]}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # Тестируем API статуса несуществующей задачи
        print("\n🔍 Тестирование /api/status/nonexistent")
        try:
            response = requests.get(f"{base_url}/api/status/nonexistent", headers=headers)
            print(f"   Статус: {response.status_code}")
            if response.status_code == 404:
                print("   ✅ Корректно возвращает 404 для несуществующей задачи")
            else:
                print(f"   ⚠️  Неожиданный статус: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    # Тестируем доступ без токена
    print(f"\n🚫 Тестирование доступа без токена")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   Статус: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Корректно блокирует доступ без токена")
        else:
            print(f"   ⚠️  Неожиданный статус: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тестируем доступ с невалидным токеном
    print(f"\n🔒 Тестирование доступа с невалидным токеном")
    try:
        headers = {'X-Identity-Token': 'invalid.token.here'}
        response = requests.get(f"{base_url}/", headers=headers)
        print(f"   Статус: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Корректно блокирует доступ с невалидным токеном")
        else:
            print(f"   ⚠️  Неожиданный статус: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

def print_test_tokens():
    """Выводит тестовые токены для ручного тестирования"""
    
    print("\n🔑 Тестовые JWT токены для ручного тестирования:")
    print("=" * 60)
    
    test_users = [
        {'user_id': 'alice', 'email': 'alice@company.com', 'name': 'Alice Johnson'},
        {'user_id': 'bob', 'email': 'bob@company.com', 'name': 'Bob Smith'},
        {'user_id': 'charlie', 'email': 'charlie@company.com', 'name': 'Charlie Brown'}
    ]
    
    for user in test_users:
        token = create_test_jwt(user['user_id'], user['email'], user['name'])
        print(f"\n👤 {user['name']} ({user['user_id']}):")
        print(f"   Email: {user['email']}")
        print(f"   Token: {token}")
        print(f"   Заголовок: X-Identity-Token: {token}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование системы аутентификации")
    parser.add_argument("--url", default="http://localhost:5000", help="URL веб-приложения")
    parser.add_argument("--tokens-only", action="store_true", help="Только вывести тестовые токены")
    
    args = parser.parse_args()
    
    if args.tokens_only:
        print_test_tokens()
    else:
        test_auth_endpoints(args.url)
        print_test_tokens()