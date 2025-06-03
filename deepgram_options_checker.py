#!/usr/bin/env python3
"""
Полная проверка всех опций Deepgram API
"""

import os
import sys
import json
import subprocess
from typing import Optional
from meeting_processor import MeetingProcessor, load_config

def check_all_deepgram_options():
    """Проверяет передачу всех опций в Deepgram"""
    
    print("🔍 ПРОВЕРКА ВСЕХ ОПЦИЙ DEEPGRAM")
    print("=" * 50)
    
    # Загружаем конфигурацию
    config = load_config("config.json")
    
    DEEPGRAM_API_KEY = config.get("api_keys", {}).get("deepgram")
    if not DEEPGRAM_API_KEY or DEEPGRAM_API_KEY == "your_deepgram_api_key_here":
        print("❌ API ключ Deepgram не настроен в config.json")
        return
    
    # Получаем текущие настройки
    deepgram_options = config.get("deepgram_options", {})
    
    print("📋 Текущие настройки в config.json:")
    for option, value in deepgram_options.items():
        status = "✅" if value else "❌"
        print(f"   {status} {option}: {value}")
    
    # Создаем процессор с текущими настройками
    processor = MeetingProcessor(
        DEEPGRAM_API_KEY,
        "test_key",
        deepgram_options=deepgram_options
    )
    
    print("\n🎤 Настройки в процессоре:")
    for option, value in processor.deepgram_options.items():
        status = "✅" if value else "❌"
        print(f"   {status} {option}: {value}")
    
    # Тестируем с коротким аудиофайлом
    test_file = input("\n📁 Введите путь к короткому аудиофайлу для тестирования (или Enter для пропуска): ").strip().strip('"')
    
    if test_file and os.path.exists(test_file):
        print(f"\n🧪 Тестирую опции на файле: {test_file}")
        
        # Создаем короткий образец
        test_sample = create_short_sample(test_file, 30)  # 30 секунд
        
        if test_sample:
            try:
                with open(test_sample, "rb") as f:
                    audio_data = f.read()
                
                # Тестируем транскрипцию с полным логированием
                try:
                    result = processor.transcribe_audio_with_timeout(audio_data, timeout_override=60)
                except Exception as e:
                    print(f"❌ Ошибка транскрипции: {e}")
                    result = None
                
                if result:
                    print("\n✅ Транскрипция успешна!")
                    print(f"📝 Длина результата: {len(result)} символов")
                    print(f"🎭 Упоминаний спикеров: {result.count('Speaker')}")
                    # Fixed: moved the split operation outside the f-string
                    line_count = len(result.split('\n'))
                    print(f"📄 Строк: {line_count}")
                    
                    # Показываем начало транскрипта
                    preview = result[:200] + "..." if len(result) > 200 else result
                    print("📖 Превью результата:")
                    print(f"   {preview}")
                else:
                    print("❌ Транскрипция не удалась")
                    
            finally:
                try:
                    os.remove(test_sample)
                except:
                    pass
        else:
            print("❌ Не удалось создать тестовый образец")
    
    else:
        print("\n⚠️ Тестирование пропущено - файл не указан или не найден")

def create_short_sample(input_file: str, duration_seconds: int = 30) -> Optional[str]:
    """Создает короткий образец для тестирования"""
    try:
        output_file = f"test_short_{duration_seconds}s.wav"
        
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-t', str(duration_seconds),
            '-acodec', 'pcm_s16le',
            '-ar', '44100',
            '-ac', '2',
            '-y',
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"📄 Создан тестовый образец: {output_file} ({duration_seconds}s)")
            return output_file
        else:
            print(f"❌ Ошибка создания образца: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def test_specific_options():
    """Тестирует конкретные комбинации опций"""
    
    print("\n🧪 ТЕСТИРОВАНИЕ КОНКРЕТНЫХ ОПЦИЙ")
    print("=" * 40)
    
    # Загружаем конфигурацию
    config = load_config("config.json")
    DEEPGRAM_API_KEY = config.get("api_keys", {}).get("deepgram")
    
    if not DEEPGRAM_API_KEY or DEEPGRAM_API_KEY == "your_deepgram_api_key_here":
        print("❌ API ключ Deepgram не настроен")
        return
    
    # Тестовые конфигурации
    test_configs = [
        {
            "name": "Минимальные настройки",
            "options": {
                "punctuate": True,
                "diarize": False,
                "smart_format": False,
                "paragraphs": False,
                "utterances": False,
                "summarize": False,
                "detect_language": False
            }
        },
        {
            "name": "Только диаризация",
            "options": {
                "punctuate": True,
                "diarize": True,
                "smart_format": False,
                "paragraphs": False,
                "utterances": False,
                "summarize": False,
                "detect_language": False
            }
        },
        {
            "name": "Полный набор (рекомендуемый)",
            "options": {
                "punctuate": True,
                "diarize": True,
                "smart_format": True,
                "paragraphs": True,
                "utterances": False,
                "summarize": False,
                "detect_language": False
            }
        },
        {
            "name": "Максимальные настройки",
            "options": {
                "punctuate": True,
                "diarize": True,
                "smart_format": True,
                "paragraphs": True,
                "utterances": True,
                "summarize": True,
                "detect_language": False
            }
        }
    ]
    
    for i, test_config in enumerate(test_configs, 1):
        print(f"\n{i}. {test_config['name']}")
        
        # Показываем настройки
        enabled_options = [k for k, v in test_config['options'].items() if v]
        disabled_options = [k for k, v in test_config['options'].items() if not v]
        
        print(f"   ✅ Включено: {', '.join(enabled_options)}")
        print(f"   ❌ Отключено: {', '.join(disabled_options)}")
        
        # Можно добавить реальное тестирование, если нужно
    
    print("\n💡 Рекомендации:")
    print("   🥇 Для встреч: используйте 'Полный набор'")
    print("   🥈 Для интервью: 'Только диаризация'")
    print("   🥉 Для лекций: 'Минимальные настройки'")

def show_options_reference():
    """Показывает справочник всех опций Deepgram"""
    
    print("\n📚 СПРАВОЧНИК ОПЦИЙ DEEPGRAM")
    print("=" * 35)
    
    options_info = {
        "punctuate": {
            "description": "Добавляет знаки препинания в транскрипт",
            "recommendation": "Всегда включено",
            "impact": "Улучшает читаемость текста",
            "default": True
        },
        "diarize": {
            "description": "Разделяет речь по спикерам (Speaker 0, Speaker 1...)",
            "recommendation": "Включить для встреч и интервью",
            "impact": "Критично для многопользовательских записей",
            "default": True
        },
        "smart_format": {
            "description": "Умное форматирование чисел, дат, валют",
            "recommendation": "Включить для деловых встреч",
            "impact": "Улучшает понимание специальных терминов",
            "default": True
        },
        "paragraphs": {
            "description": "Разделяет текст на смысловые параграфы",
            "recommendation": "Включить для длинных записей",
            "impact": "Структурирует текст, улучшает читаемость",
            "default": True
        },
        "utterances": {
            "description": "Добавляет метаданные о каждом высказывании",
            "recommendation": "Для детального анализа",
            "impact": "Подробная информация о времени и спикерах",
            "default": False
        },
        "summarize": {
            "description": "Автоматическое создание краткого изложения",
            "recommendation": "Отключить (конфликтует с Claude)",
            "impact": "Deepgram создает собственное резюме",
            "default": False
        },
        "detect_language": {
            "description": "Автоматическое определение языка",
            "recommendation": "Только для многоязычных записей",
            "impact": "Может замедлить обработку",
            "default": False
        }
    }
    
    for option, info in options_info.items():
        status = "✅" if info["default"] else "❌"
        print(f"\n{status} {option.upper()}")
        print(f"   📝 {info['description']}")
        print(f"   💡 {info['recommendation']}")
        print(f"   🎯 {info['impact']}")

def main():
    """Основная функция"""
    
    print("🔍 АНАЛИЗАТОР ОПЦИЙ DEEPGRAM")
    print("=" * 40)
    
    print("Выберите действие:")
    print("1. Проверить текущие настройки")
    print("2. Тестировать конкретные опции")
    print("3. Справочник всех опций")
    print("4. Выполнить все проверки")
    print("5. Выход")
    
    choice = input("\nВведите номер (1-5): ").strip()
    
    if choice == "1":
        check_all_deepgram_options()
    elif choice == "2":
        test_specific_options()
    elif choice == "3":
        show_options_reference()
    elif choice == "4":
        check_all_deepgram_options()
        test_specific_options()
        show_options_reference()
    elif choice == "5":
        print("👋 До свидания!")
    else:
        print("❌ Неверный выбор")

if __name__ == "__main__":
    main()