#!/usr/bin/env python3
"""
Скрипт для тестирования поддержки различных форматов файлов
"""

import os
from pathlib import Path
from meeting_processor import MeetingProcessor, load_config

def test_file_format(file_path: str):
    """Тестирует формат файла"""
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return
    
    # Создаем фиктивный процессор для тестирования
    processor = MeetingProcessor("test", "test")
    
    # Анализируем файл
    file_type, file_ext, file_info = processor.get_audio_info(file_path)
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    print(f"\n📁 Файл: {Path(file_path).name}")
    print(f"📊 Размер: {file_size_mb:.1f} MB")
    print(f"🔍 Расширение: {file_ext}")
    print(f"⚙️ Тип обработки: {file_type}")
    print(f"ℹ️  {file_info}")
    
    # Рекомендации по обработке
    if file_type == "native_audio":
        print("✨ 🚀 ОПТИМАЛЬНО! Нативная поддержка Deepgram")
        print("   ⚡ Быстрая обработка без конвертации")
        print("   🎯 Максимальное качество")
        
    elif file_type == "convert_audio":
        print("🔄 Требуется конвертация в WAV")
        print("   ⏱️ Дополнительное время на конвертацию")
        print("   💽 Временный файл на диске")
        
    elif file_type == "video":
        print("🎬 Извлечение аудиодорожки")
        print("   ⏱️ Время на извлечение аудио")
        print("   💽 Временный WAV файл")
        
    else:
        print("❌ Неподдерживаемый формат")
        return
    
    # Оценка времени обработки
    if file_size_mb < 5:
        time_estimate = "< 1 минуты"
    elif file_size_mb < 15:
        time_estimate = "1-3 минуты"  
    elif file_size_mb < 50:
        time_estimate = "3-10 минут"
    else:
        time_estimate = "> 10 минут"
    
    print(f"⏱️ Примерное время обработки: {time_estimate}")

def show_format_comparison():
    """Показывает сравнение форматов"""
    print("📊 СРАВНЕНИЕ ФОРМАТОВ")
    print("=" * 60)
    
    formats = [
        ("MP3", "native_audio", "⚡⚡⚡", "🎯", "✅ Нативная поддержка"),
        ("WAV", "native_audio", "⚡⚡⚡", "🎯", "✅ Нативная поддержка"),
        ("FLAC", "native_audio", "⚡⚡⚡", "🎯", "✅ Нативная поддержка"),
        ("AAC", "native_audio", "⚡⚡⚡", "🎯", "✅ Нативная поддержка"),
        ("M4A", "native_audio", "⚡⚡⚡", "🎯", "✅ Нативная поддержка"),
        ("OGG", "native_audio", "⚡⚡⚡", "🎯", "✅ Нативная поддержка"),
        ("WMA", "convert_audio", "⚡⚡", "🔄", "🔄 Конвертация в WAV"),
        ("OPUS", "convert_audio", "⚡⚡", "🔄", "🔄 Конвертация в WAV"),
        ("MP4", "video", "⚡", "🎬", "🎬 Извлечение аудио"),
        ("AVI", "video", "⚡", "🎬", "🎬 Извлечение аудио"),
        ("MOV", "video", "⚡", "🎬", "🎬 Извлечение аудио")
    ]
    
    print(f"{'Формат':<8} {'Скорость':<10} {'Качество':<10} {'Обработка'}")
    print("-" * 60)
    
    for fmt, ftype, speed, quality, processing in formats:
        print(f"{fmt:<8} {speed:<10} {quality:<10} {processing}")
    
    print(f"\n💡 Рекомендации:")
    print(f"🥇 Лучший выбор: MP3, WAV, FLAC - нативная поддержка")
    print(f"🥈 Хороший выбор: AAC, M4A, OGG - нативная поддержка") 
    print(f"🥉 Средний выбор: WMA, OPUS - требуют конвертации")
    print(f"📹 Видео: Все форматы поддерживаются через извлечение аудио")

def show_deepgram_native_formats():
    """Показывает форматы с нативной поддержкой Deepgram"""
    print("\n🎤 НАТИВНАЯ ПОДДЕРЖКА DEEPGRAM")
    print("=" * 50)
    
    native_formats = [
        ("MP3", "Самый популярный формат, отличная поддержка"),
        ("WAV", "Несжатый формат, максимальное качество"),
        ("FLAC", "Lossless сжатие, отличное качество"),
        ("AAC", "Современный формат, хорошее сжатие"),
        ("M4A", "Apple формат, хорошая поддержка"),
        ("OGG", "Открытый формат, хорошее качество")
    ]
    
    for fmt, description in native_formats:
        print(f"✅ {fmt:<6} - {description}")
    
    print(f"\n🚀 Преимущества нативной поддержки:")
    print(f"   ⚡ Быстрая обработка без конвертации")
    print(f"   🎯 Сохранение оригинального качества")
    print(f"   💽 Экономия дискового пространства")
    print(f"   🔒 Большая надежность процесса")

def main():
    """Основная функция"""
    print("🧪 ТЕСТ ПОДДЕРЖКИ ФОРМАТОВ ФАЙЛОВ")
    print("=" * 50)
    
    print("Выберите действие:")
    print("1. Проверить конкретный файл")
    print("2. Показать сравнение форматов")
    print("3. Показать нативные форматы Deepgram")
    print("4. Проверить все файлы в папке")
    print("5. Выйти")
    
    choice = input("\nВведите номер (1-5): ").strip()
    
    if choice == "1":
        # Проверка конкретного файла
        file_path = input("📁 Введите путь к файлу: ").strip().strip('"')
        test_file_format(file_path)
        
    elif choice == "2":
        # Сравнение форматов
        show_format_comparison()
        
    elif choice == "3":
        # Нативные форматы
        show_deepgram_native_formats()
        
    elif choice == "4":
        # Проверка всех файлов в папке
        folder_path = input("📁 Введите путь к папке: ").strip().strip('"')
        
        if os.path.exists(folder_path):
            media_extensions = {'.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', 
                              '.wma', '.opus', '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm'}
            
            files_found = []
            for file_path in Path(folder_path).iterdir():
                if file_path.suffix.lower() in media_extensions:
                    files_found.append(str(file_path))
            
            if files_found:
                print(f"\n🔍 Найдено {len(files_found)} медиафайлов:")
                for file_path in sorted(files_found):
                    test_file_format(file_path)
            else:
                print("❌ Медиафайлы не найдены в указанной папке")
        else:
            print("❌ Папка не найдена")
            
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