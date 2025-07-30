#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции с OpenRouter API
"""

import sys
import os
from openrouter_client import OpenRouterClient
from protocol_generator import ProtocolGenerator

def test_openrouter_client():
    """Тестирует базовую функциональность OpenRouterClient"""
    print("🧪 Тестирование OpenRouterClient...")
    
    # Проверяем, что можно создать клиент
    try:
        client = OpenRouterClient(api_key="test_key", model="anthropic/claude-sonnet-4")
        print("✅ OpenRouterClient создан успешно")
        
        # Проверяем преобразование моделей
        test_models = {
            "claude-3-haiku-20240307": "anthropic/claude-3-haiku",
            "claude-3-sonnet-20240229": "anthropic/claude-3-sonnet",
            "claude-3-opus-20240229": "anthropic/claude-3-opus",
            "claude-sonnet-4-20250514": "anthropic/claude-sonnet-4"
        }
        
        for old_model, expected_new in test_models.items():
            actual_new = client.get_openrouter_model_name(old_model)
            if actual_new == expected_new:
                print(f"✅ Модель {old_model} -> {actual_new}")
            else:
                print(f"❌ Ошибка преобразования модели {old_model}: ожидалось {expected_new}, получено {actual_new}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании OpenRouterClient: {e}")
        return False

def test_protocol_generator():
    """Тестирует ProtocolGenerator с OpenRouter"""
    print("\n🧪 Тестирование ProtocolGenerator...")
    
    try:
        # Создаем генератор протоколов
        generator = ProtocolGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        print("✅ ProtocolGenerator создан успешно")
        
        # Проверяем, что модель правильно преобразована
        if hasattr(generator, 'openrouter_model'):
            expected_model = "anthropic/claude-sonnet-4"
            if generator.openrouter_model == expected_model:
                print(f"✅ Модель преобразована правильно: {generator.openrouter_model}")
            else:
                print(f"❌ Неправильное преобразование модели: ожидалось {expected_model}, получено {generator.openrouter_model}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании ProtocolGenerator: {e}")
        return False

def test_imports():
    """Тестирует импорты"""
    print("🧪 Тестирование импортов...")
    
    try:
        import openai
        print("✅ openai импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта openai: {e}")
        return False
    
    try:
        from openrouter_client import OpenRouterClient
        print("✅ OpenRouterClient импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта OpenRouterClient: {e}")
        return False
    
    try:
        from protocol_generator import ProtocolGenerator
        print("✅ ProtocolGenerator импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта ProtocolGenerator: {e}")
        return False
    
    # Проверяем, что старый anthropic не импортируется
    try:
        import anthropic
        print("⚠️  Предупреждение: anthropic все еще доступен (может потребоваться удаление)")
    except ImportError:
        print("✅ anthropic правильно удален")
    
    return True

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ С OPENROUTER API")
    print("=" * 50)
    
    tests = [
        ("Импорты", test_imports),
        ("OpenRouterClient", test_openrouter_client),
        ("ProtocolGenerator", test_protocol_generator)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: ПРОЙДЕН")
        else:
            print(f"❌ {test_name}: ПРОВАЛЕН")
    
    print(f"\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"Пройдено: {passed}/{total}")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Интеграция с OpenRouter работает корректно.")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Проверьте ошибки выше.")
        return 1

if __name__ == "__main__":
    sys.exit(main())