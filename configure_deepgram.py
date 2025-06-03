#!/usr/bin/env python3
"""
Скрипт для настройки опций Deepgram API
"""

import json
import os
from meeting_processor import load_config

def show_deepgram_options():
    """Показывает доступные опции Deepgram"""
    options = {
        "punctuate": {
            "description": "Добавляет знаки препинания в транскрипт",
            "default": True,
            "impact": "Улучшает читаемость текста",
            "recommended": "Всегда включено"
        },
        "diarize": {
            "description": "Разделяет речь по спикерам (Speaker 0, Speaker 1, ...)",
            "default": True,
            "impact": "Позволяет различать участников встречи",
            "recommended": "Обязательно для встреч"
        },
        "smart_format": {
            "description": "Умное форматирование (числа, даты, валюты)",
            "default": True,
            "impact": "Улучшает качество распознавания специальных терминов",
            "recommended": "Включено для деловых встреч"
        },
        "paragraphs": {
            "description": "Разделяет текст на параграфы по смысловым блокам",
            "default": True,
            "impact": "Структурирует текст, улучшает читаемость",
            "recommended": "Очень полезно для длинных записей"
        },
        "utterances": {
            "description": "Добавляет метаданные о каждом высказывании",
            "default": False,
            "impact": "Подробная информация о времени и спикерах",
            "recommended": "Для детального анализа"
        },
        "summarize": {
            "description": "Автоматическое создание краткого изложения",
            "default": False,
            "impact": "Deepgram создает собственное резюме",
            "recommended": "Конфликтует с Claude, лучше отключить"
        },
        "detect_language": {
            "description": "Автоматическое определение языка",
            "default": False,
            "impact": "Полезно для многоязычных встреч",
            "recommended": "Включить только при необходимости"
        }
    }
    
    print("🎤 ОПЦИИ DEEPGRAM API")
    print("=" * 60)
    
    for option, info in options.items():
        status = "✅" if info["default"] else "❌"
        print(f"\n{status} {option.upper()}")
        print(f"   📝 {info['description']}")
        print(f"   🎯 Влияние: {info['impact']}")
        print(f"   💡 Рекомендация: {info['recommended']}")
    
    return options

def get_current_config():
    """Получает текущую конфигурацию Deepgram"""
    config = load_config("config.json")
    return config.get("deepgram_options", {})

def update_deepgram_options(new_options):
    """Обновляет опции Deepgram в конфигурации"""
    try:
        config = load_config("config.json")
        if not config:
            print("❌ Не удалось загрузить config.json")
            return False
        
        # Обновляем опции
        config["deepgram_options"] = new_options
        
        # Сохраняем обновленную конфигурацию
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print("✅ Конфигурация Deepgram обновлена!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении конфигурации: {e}")
        return False

def interactive_config():
    """Интерактивная настройка опций"""
    print("🔧 ИНТЕРАКТИВНАЯ НАСТРОЙКА DEEPGRAM")
    print("=" * 50)
    
    options_info = show_deepgram_options()
    current_config = get_current_config()
    
    print(f"\n📊 Текущие настройки:")
    for option, value in current_config.items():
        status = "✅" if value else "❌"
        print(f"   {status} {option}")
    
    print(f"\nНастройка опций (y/n для каждой опции):")
    new_config = {}
    
    for option, info in options_info.items():
        current_value = current_config.get(option, info["default"])
        current_status = "включена" if current_value else "отключена"
        
        print(f"\n🎤 {option.upper()}")
        print(f"   📝 {info['description']}")
        print(f"   📊 Текущий статус: {current_status}")
        print(f"   💡 Рекомендация: {info['recommended']}")
        
        while True:
            choice = input(f"   Включить {option}? (y/n) [текущее: {'y' if current_value else 'n'}]: ").strip().lower()
            
            if choice == '':
                new_config[option] = current_value
                break
            elif choice in ['y', 'yes', 'да']:
                new_config[option] = True
                break
            elif choice in ['n', 'no', 'нет']:
                new_config[option] = False
                break
            else:
                print("   ❌ Введите y (да) или n (нет)")
    
    # Показываем итоговую конфигурацию
    print(f"\n📋 ИТОГОВАЯ КОНФИГУРАЦИЯ:")
    print("=" * 30)
    for option, value in new_config.items():
        status = "✅" if value else "❌"
        print(f"   {status} {option}")
    
    # Подтверждение
    confirm = input(f"\nСохранить эту конфигурацию? (y/n): ").strip().lower()
    
    if confirm in ['y', 'yes', 'да']:
        if update_deepgram_options(new_config):
            print(f"\n🎉 Конфигурация сохранена!")
            return True
        else:
            print(f"\n❌ Ошибка при сохранении")
            return False
    else:
        print(f"\n🚫 Изменения отменены")
        return False

def preset_configs():
    """Предустановленные конфигурации"""
    presets = {
        "basic": {
            "name": "Базовая",
            "description": "Минимальные настройки для простых встреч",
            "config": {
                "punctuate": True,
                "diarize": True,
                "smart_format": False,
                "paragraphs": False,
                "utterances": False,
                "summarize": False,
                "detect_language": False
            }
        },
        "standard": {
            "name": "Стандартная",
            "description": "Рекомендуемые настройки для большинства встреч",
            "config": {
                "punctuate": True,
                "diarize": True,
                "smart_format": True,
                "paragraphs": True,
                "utterances": False,
                "summarize": False,
                "detect_language": False
            }
        },
        "advanced": {
            "name": "Продвинутая",
            "description": "Максимальные возможности для детального анализа",
            "config": {
                "punctuate": True,
                "diarize": True,
                "smart_format": True,
                "paragraphs": True,
                "utterances": True,
                "summarize": False,
                "detect_language": False
            }
        },
        "multilingual": {
            "name": "Многоязычная",
            "description": "Для встреч на разных языках",
            "config": {
                "punctuate": True,
                "diarize": True,
                "smart_format": True,
                "paragraphs": True,
                "utterances": False,
                "summarize": False,
                "detect_language": True
            }
        }
    }
    
    print("🎯 ПРЕДУСТАНОВЛЕННЫЕ КОНФИГУРАЦИИ")
    print("=" * 50)
    
    for i, (key, preset) in enumerate(presets.items(), 1):
        print(f"\n{i}. {preset['name']}")
        print(f"   📝 {preset['description']}")
        print(f"   🎤 Опции: {', '.join([k for k, v in preset['config'].items() if v])}")
    
    choice = input(f"\nВыберите конфигурацию (1-{len(presets)}) или Enter для отмены: ").strip()
    
    if choice.isdigit() and 1 <= int(choice) <= len(presets):
        preset_key = list(presets.keys())[int(choice) - 1]
        selected_preset = presets[preset_key]
        
        print(f"\n✅ Выбрана конфигурация: {selected_preset['name']}")
        
        if update_deepgram_options(selected_preset['config']):
            print("🎉 Конфигурация применена!")
            return True
        else:
            print("❌ Ошибка при применении конфигурации")
            return False
    else:
        print("🚫 Отменено")
        return False

def main():
    """Основная функция"""
    print("🎤 НАСТРОЙКА DEEPGRAM API")
    print("=" * 40)
    
    print("Выберите действие:")
    print("1. Показать текущие настройки")
    print("2. Интерактивная настройка")
    print("3. Использовать предустановленную конфигурацию")
    print("4. Показать описание всех опций")
    print("5. Выйти")
    
    choice = input("\nВведите номер (1-5): ").strip()
    
    if choice == "1":
        # Показать текущие настройки
        current_config = get_current_config()
        if current_config:
            print("\n📊 Текущие настройки Deepgram:")
            print("=" * 30)
            for option, value in current_config.items():
                status = "✅" if value else "❌"
                print(f"   {status} {option}")
        else:
            print("\n❌ Настройки Deepgram не найдены в config.json")
    
    elif choice == "2":
        # Интерактивная настройка
        interactive_config()
    
    elif choice == "3":
        # Предустановленные конфигурации
        preset_configs()
    
    elif choice == "4":
        # Описание опций
        show_deepgram_options()
    
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