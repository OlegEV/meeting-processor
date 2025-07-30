#!/usr/bin/env python3
"""
Скрипт для выбора и тестирования моделей Claude через OpenRouter
"""

import json
import os
from meeting_processor import load_config

def show_claude_models():
    """Показывает доступные модели Claude"""
    models = {
        "claude-3-haiku-20240307": {
            "name": "Claude 3 Haiku",
            "description": "Быстрая и экономичная модель для простых задач",
            "speed": "⚡⚡⚡",
            "quality": "⭐⭐⭐",
            "cost": "💰",
            "best_for": "Простые резюме, быстрая обработка"
        },
        "claude-3-sonnet-20240229": {
            "name": "Claude 3 Sonnet", 
            "description": "Сбалансированная модель для большинства задач",
            "speed": "⚡⚡",
            "quality": "⭐⭐⭐⭐",
            "cost": "💰💰",
            "best_for": "Протоколы встреч, анализ текста (рекомендуется)"
        },
        "claude-3-opus-20240229": {
            "name": "Claude 3 Opus",
            "description": "Самая мощная модель для сложных задач",
            "speed": "⚡",
            "quality": "⭐⭐⭐⭐⭐",
            "cost": "💰💰💰",
            "best_for": "Детальный анализ, сложные протоколы"
        },
        "claude-sonnet-4-20250514": {
            "name": "Claude Sonnet 4",
            "description": "Новейшая модель с улучшенными возможностями",
            "speed": "⚡⚡",
            "quality": "⭐⭐⭐⭐⭐",
            "cost": "💰💰💰",
            "best_for": "Современные возможности, лучшее качество"
        }
    }
    
    print("🤖 ДОСТУПНЫЕ МОДЕЛИ CLAUDE")
    print("=" * 60)
    
    for i, (model_id, info) in enumerate(models.items(), 1):
        print(f"\n{i}. {info['name']} ({model_id})")
        print(f"   📝 {info['description']}")
        print(f"   🚀 Скорость: {info['speed']}")
        print(f"   ⭐ Качество: {info['quality']}")
        print(f"   💰 Стоимость: {info['cost']}")
        print(f"   🎯 Лучше всего для: {info['best_for']}")
    
    return models

def update_config_model(config_file: str, new_model: str):
    """Обновляет модель в конфигурации"""
    try:
        config = load_config(config_file)
        if not config:
            print(f"❌ Не удалось загрузить {config_file}")
            return False
        
        # Обновляем модель
        if "settings" not in config:
            config["settings"] = {}
        
        old_model = config["settings"].get("claude_model", "не указана")
        config["settings"]["claude_model"] = new_model
        
        # Сохраняем обновленную конфигурацию
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Конфигурация обновлена:")
        print(f"   Старая модель: {old_model}")
        print(f"   Новая модель: {new_model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении конфигурации: {e}")
        return False

def test_claude_model(model_id: str, api_key: str):
    """Тестирует модель Claude через OpenRouter"""
    try:
        from openrouter_client import OpenRouterClient
        
        print(f"🧪 Тестирую модель {model_id} через OpenRouter...")
        
        # Преобразуем модель в формат OpenRouter
        model_mapping = {
            "claude-3-haiku-20240307": "anthropic/claude-3-haiku",
            "claude-3-sonnet-20240229": "anthropic/claude-3-sonnet",
            "claude-3-opus-20240229": "anthropic/claude-3-opus",
            "claude-sonnet-4-20250514": "anthropic/claude-sonnet-4"
        }
        openrouter_model = model_mapping.get(model_id, "anthropic/claude-sonnet-4")
        
        client = OpenRouterClient(api_key=api_key, model=openrouter_model)
        
        test_prompt = """
Создай краткий тестовый протокол встречи на основе этого примера:

"Сегодня обсуждали планы на следующий квартал. Решили увеличить бюджет на маркетинг на 20%. Ответственный - Иванов. Срок - до конца месяца."

Протокол должен содержать разделы: Решения, Ответственные, Сроки.
"""
        
        result = client.create_message_anthropic_format(
            content=test_prompt,
            max_tokens=500
        )
        
        if not result:
            print(f"❌ Не удалось получить ответ от OpenRouter API")
            return False
        
        print(f"✅ Модель {model_id} ({openrouter_model}) работает!")
        print(f"📝 Пример ответа:")
        print("-" * 40)
        print(result[:300] + "..." if len(result) > 300 else result)
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании модели {model_id}: {e}")
        return False

def main():
    """Основная функция"""
    print("🔧 НАСТРОЙКА МОДЕЛИ CLAUDE")
    print("=" * 40)
    
    # Показываем доступные модели
    models = show_claude_models()
    model_list = list(models.keys())
    
    # Загружаем текущую конфигурацию
    config = load_config("config.json")
    current_model = config.get("settings", {}).get("claude_model", "не указана")
    
    print(f"\n📊 Текущая модель: {current_model}")
    
    # Спрашиваем, что делать
    print(f"\nВыберите действие:")
    print(f"1. Изменить модель в конфигурации")
    print(f"2. Протестировать текущую модель")
    print(f"3. Протестировать другую модель")
    print(f"4. Показать рекомендации")
    print(f"5. Выйти")
    
    choice = input(f"\nВведите номер (1-5): ").strip()
    
    if choice == "1":
        # Изменение модели
        print(f"\nВыберите новую модель (1-{len(model_list)}):")
        model_choice = input("Номер модели: ").strip()
        
        if model_choice.isdigit() and 1 <= int(model_choice) <= len(model_list):
            new_model = model_list[int(model_choice) - 1]
            
            if update_config_model("config.json", new_model):
                print(f"\n🎉 Модель успешно изменена на {new_model}")
            
        else:
            print("❌ Неверный номер модели")
    
    elif choice == "2":
        # Тест текущей модели
        api_key = config.get("api_keys", {}).get("claude")
        
        if not api_key or api_key == "your_claude_api_key_here":
            print("❌ API ключ Claude не настроен в config.json")
            print("💡 Теперь используется OpenRouter API - обновите ключ на OpenRouter API ключ")
            return
        
        if current_model != "не указана":
            test_claude_model(current_model, api_key)
        else:
            print("❌ Модель не указана в конфигурации")
    
    elif choice == "3":
        # Тест другой модели
        api_key = config.get("api_keys", {}).get("claude")
        
        if not api_key or api_key == "your_claude_api_key_here":
            print("❌ API ключ Claude не настроен в config.json")
            print("💡 Теперь используется OpenRouter API - обновите ключ на OpenRouter API ключ")
            return
        
        print(f"\nВыберите модель для тестирования (1-{len(model_list)}):")
        model_choice = input("Номер модели: ").strip()
        
        if model_choice.isdigit() and 1 <= int(model_choice) <= len(model_list):
            test_model = model_list[int(model_choice) - 1]
            test_claude_model(test_model, api_key)
        else:
            print("❌ Неверный номер модели")
    
    elif choice == "4":
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ ПО ВЫБОРУ МОДЕЛИ:")
        print(f"=" * 50)
        
        recommendations = [
            ("Короткие встречи (< 30 мин)", "Claude 3 Haiku", "Быстро и экономично"),
            ("Обычные встречи (30-60 мин)", "Claude 3 Sonnet", "Оптимальное соотношение цена/качество"),
            ("Длинные встречи (> 60 мин)", "Claude 3 Sonnet", "Хорошо справляется с большими объемами"),
            ("Важные встречи", "Claude 3 Opus", "Максимальное качество анализа"),
            ("Новые возможности", "Claude Sonnet 4", "Самые современные функции")
        ]
        
        for scenario, model, reason in recommendations:
            print(f"📋 {scenario}")
            print(f"   🤖 Рекомендуется: {model}")
            print(f"   💭 Причина: {reason}")
            print()
        
        print("🔄 ВАЖНО: Теперь система использует OpenRouter API")
        print("   Убедитесь, что у вас есть действующий API ключ OpenRouter")
        print("   Обновите ключ в config.json в разделе api_keys.claude")
    
    elif choice == "5":
        print("👋 До свидания!")
        return
    
    else:
        print("❌ Неверный выбор")
    
    # Предлагаем запустить еще раз
    if input(f"\nЗапустить еще раз? (y/n): ").lower().startswith('y'):
        main()

if __name__ == "__main__":
    main()