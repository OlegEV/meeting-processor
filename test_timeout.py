#!/usr/bin/env python3
"""
Скрипт для тестирования настроек таймаута Deepgram
"""

import os
import time
from pathlib import Path
from meeting_processor import MeetingProcessor, load_config

def test_timeout_settings():
    """Тестирует различные настройки таймаута"""
    
    print("🧪 ТЕСТ НАСТРОЕК ТАЙМАУТА DEEPGRAM")
    print("=" * 50)
    
    # Загружаем конфигурацию
    config = load_config("config.json")
    
    DEEPGRAM_API_KEY = config.get("api_keys", {}).get("deepgram")
    CLAUDE_API_KEY = config.get("api_keys", {}).get("claude")
    
    if not DEEPGRAM_API_KEY or DEEPGRAM_API_KEY == "your_deepgram_api_key_here":
        print("❌ Укажите API ключ Deepgram в config.json")
        return
    
    # Тестируем разные таймауты
    timeout_settings = [
        (60, "1 минута - для быстрых тестов"),
        (180, "3 минуты - для коротких файлов"), 
        (300, "5 минут - стандартная настройка"),
        (600, "10 минут - для длинных файлов"),
        (900, "15 минут - максимальный таймаут")
    ]
    
    # Запрашиваем тестовый файл
    test_file = input("📁 Введите путь к тестовому аудиофайлу (или Enter для пропуска): ").strip().strip('"')
    
    if not test_file or not os.path.exists(test_file):
        print("⚠️ Файл не указан или не найден. Показываю только настройки.")
        show_timeout_recommendations()
        return
    
    # Получаем информацию о файле
    file_size_mb = os.path.getsize(test_file) / (1024 * 1024)
    print(f"\n📊 Тестовый файл: {test_file}")
    print(f"📏 Размер: {file_size_mb:.1f} MB")
    
    # Определяем рекомендуемый таймаут
    if file_size_mb < 5:
        recommended_timeout = 180
    elif file_size_mb < 15:
        recommended_timeout = 300
    elif file_size_mb < 30:
        recommended_timeout = 600
    else:
        recommended_timeout = 900
    
    print(f"💡 Рекомендуемый таймаут: {recommended_timeout} секунд")
    
    # Спрашиваем, какой таймаут тестировать
    print(f"\nДоступные варианты:")
    for i, (timeout, desc) in enumerate(timeout_settings, 1):
        marker = "👈 рекомендуется" if timeout == recommended_timeout else ""
        print(f"{i}. {timeout} сек - {desc} {marker}")
    
    choice = input(f"\nВыберите таймаут (1-{len(timeout_settings)}) или Enter для рекомендуемого: ").strip()
    
    if choice.isdigit() and 1 <= int(choice) <= len(timeout_settings):
        selected_timeout, desc = timeout_settings[int(choice) - 1]
    else:
        selected_timeout, desc = recommended_timeout, "рекомендуемый"
    
    print(f"\n🚀 Тестирую с таймаутом {selected_timeout} секунд ({desc})")
    
    # Создаем процессор с выбранным таймаутом
    processor = MeetingProcessor(DEEPGRAM_API_KEY, CLAUDE_API_KEY, selected_timeout)
    
    # Подготавливаем аудиофайл
    output_dir = "timeout_test"
    Path(output_dir).mkdir(exist_ok=True)
    
    test_name = Path(test_file).stem
    audio_path = f"{output_dir}/{test_name}_test.wav"
    
    # Проверяем тип файла и обрабатываем
    is_audio_file, file_ext, file_info = processor.get_audio_info(test_file)
    print(f"📄 Тип файла: {'Аудио' if is_audio_file else 'Видео'} ({file_ext})")
    
    start_time = time.time()
    
    if is_audio_file:
        success = processor.process_audio_file(test_file, audio_path)
    else:
        success = processor.extract_audio_from_video(test_file, audio_path)
    
    if not success:
        print("❌ Не удалось подготовить аудиофайл")
        return
    
    # Тестируем транскрипцию
    print(f"\n⏱️ Начинаю тест транскрипции с таймаутом {selected_timeout} сек...")
    
    try:
        with open(audio_path, "rb") as file:
            audio_data = file.read()
        
        transcript = processor.transcribe_audio_with_timeout(audio_data, selected_timeout)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if transcript:
            print(f"✅ Успех! Время выполнения: {duration:.1f} секунд")
            print(f"📝 Длина транскрипта: {len(transcript)} символов")
            print(f"📄 Первые 200 символов: {transcript[:200]}...")
            
            # Сохраняем результат
            result_path = f"{output_dir}/test_result_{selected_timeout}s.txt"
            with open(result_path, "w", encoding="utf-8") as f:
                f.write(f"Таймаут: {selected_timeout} секунд\n")
                f.write(f"Время выполнения: {duration:.1f} секунд\n")
                f.write(f"Размер файла: {file_size_mb:.1f} MB\n\n")
                f.write(transcript)
            
            print(f"💾 Результат сохранен в {result_path}")
        else:
            print(f"❌ Неудача! Время до отказа: {duration:.1f} секунд")
            
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"💥 Ошибка после {duration:.1f} секунд: {e}")
    
    # Очистка
    try:
        os.remove(audio_path)
    except:
        pass
    
    print(f"\n📋 Результаты теста:")
    print(f"   Таймаут: {selected_timeout} секунд")
    print(f"   Файл: {file_size_mb:.1f} MB")
    print(f"   Время: {duration:.1f} секунд")
    print(f"   Статус: {'✅ Успех' if transcript else '❌ Неудача'}")

def show_timeout_recommendations():
    """Показывает рекомендации по настройке таймаута"""
    print("\n💡 РЕКОМЕНДАЦИИ ПО НАСТРОЙКЕ ТАЙМАУТА:")
    print("=" * 50)
    
    recommendations = [
        ("< 2 MB", "< 5 минут", "60-180 сек", "Короткие записи"),
        ("2-10 MB", "5-15 минут", "180-300 сек", "Средние файлы"),
        ("10-25 MB", "15-30 минут", "300-600 сек", "Длинные записи"),
        ("25-50 MB", "30-60 минут", "600-900 сек", "Очень длинные"),
        ("> 50 MB", "> 60 минут", "900+ сек", "Используйте разбивку")
    ]
    
    print(f"{'Размер файла':<12} {'Длительность':<15} {'Таймаут':<15} {'Описание'}")
    print("-" * 65)
    
    for size, duration, timeout, desc in recommendations:
        print(f"{size:<12} {duration:<15} {timeout:<15} {desc}")
    
    print(f"\n📝 Настройка в config.json:")
    print(f'   "deepgram_timeout_seconds": 300')
    
    print(f"\n⚙️ Дополнительные настройки:")
    print(f"   • Для надежности используйте разбивку файлов > 25MB")
    print(f"   • Добавьте паузы между запросами (request_pause_seconds: 5)")
    print(f"   • Настройте повторные попытки (max_retries: 3)")

def main():
    """Основная функция"""
    test_timeout_settings()
    
    print(f"\n🎯 Следующие шаги:")
    print(f"1. Обновите config.json с оптимальным таймаутом")
    print(f"2. Для больших файлов используйте process_long_audio.py")
    print(f"3. При частых таймаутах увеличьте значение или используйте разбивку")

if __name__ == "__main__":
    main()