#!/usr/bin/env python3
"""
Скрипт для извлечения и анализа даты/времени аудио и видео файлов
"""

import os
import sys
from pathlib import Path
import datetime
from meeting_processor import MeetingProcessor

def analyze_file_datetime(file_path: str):
    """Анализирует дату и время файла"""
    
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return
    
    # Создаем процессор для получения информации
    processor = MeetingProcessor("test", "test")
    
    print(f"📁 АНАЛИЗ ФАЙЛА: {Path(file_path).name}")
    print("=" * 50)
    
    # Получаем базовую информацию о файле
    file_type, file_ext, file_info = processor.get_audio_info(file_path)
    print(f"📊 Тип файла: {file_type} ({file_ext})")
    print(f"ℹ️  {file_info}")
    
    # Получаем информацию о дате и времени
    datetime_info = processor.get_file_datetime_info(file_path)
    
    print(f"\n📅 ИНФОРМАЦИЯ О ДАТЕ И ВРЕМЕНИ:")
    print("=" * 35)
    print(f"📅 Дата: {datetime_info['date']}")
    print(f"⏰ Время: {datetime_info['time']}")
    print(f"📋 Полная дата/время: {datetime_info['datetime_full']}")
    print(f"📆 День недели: {datetime_info['weekday_ru']}")
    print(f"🗓️ Месяц: {datetime_info['month_ru']}")
    
    # Анализируем время создания
    file_age = datetime.datetime.now() - datetime_info['datetime']
    
    if file_age.days == 0:
        age_str = "сегодня"
    elif file_age.days == 1:
        age_str = "вчера"
    elif file_age.days < 7:
        age_str = f"{file_age.days} дней назад"
    elif file_age.days < 30:
        weeks = file_age.days // 7
        age_str = f"{weeks} недель назад"
    elif file_age.days < 365:
        months = file_age.days // 30
        age_str = f"{months} месяцев назад"
    else:
        years = file_age.days // 365
        age_str = f"{years} лет назад"
    
    print(f"⏳ Возраст файла: {age_str}")
    
    # Определяем время дня
    hour = datetime_info['datetime'].hour
    if 5 <= hour < 12:
        time_of_day = "утром"
    elif 12 <= hour < 17:
        time_of_day = "днем"
    elif 17 <= hour < 22:
        time_of_day = "вечером"
    else:
        time_of_day = "ночью"
    
    print(f"🌅 Время суток: {time_of_day}")
    
    # Предполагаемый тип встречи по времени
    if datetime_info['weekday_ru'] in ['суббота', 'воскресенье']:
        meeting_type = "выходной день (возможно личная встреча)"
    elif 9 <= hour <= 18:
        meeting_type = "рабочее время (деловая встреча)"
    elif 18 < hour <= 22:
        meeting_type = "вечернее время (неформальная встреча)"
    else:
        meeting_type = "нестандартное время"
    
    print(f"💼 Предполагаемый тип: {meeting_type}")

def analyze_filename_patterns(file_path: str):
    """Анализирует паттерны в имени файла"""
    
    filename = Path(file_path).stem
    print(f"\n🔍 АНАЛИЗ ИМЕНИ ФАЙЛА:")
    print("=" * 25)
    print(f"📝 Имя файла: {filename}")
    
    # Ищем паттерны даты в имени файла
    import re
    
    # Паттерны дат
    date_patterns = [
        (r'(\d{4})-(\d{2})-(\d{2})', 'YYYY-MM-DD'),
        (r'(\d{2})\.(\d{2})\.(\d{4})', 'DD.MM.YYYY'),
        (r'(\d{2})/(\d{2})/(\d{4})', 'DD/MM/YYYY'),
        (r'(\d{8})', 'YYYYMMDD'),
    ]
    
    # Паттерны времени
    time_patterns = [
        (r'(\d{2}):(\d{2}):(\d{2})', 'HH:MM:SS'),
        (r'(\d{2})-(\d{2})-(\d{2})', 'HH-MM-SS'),
        (r'(\d{6})', 'HHMMSS'),
    ]
    
    found_dates = []
    found_times = []
    
    for pattern, format_desc in date_patterns:
        matches = re.findall(pattern, filename)
        if matches:
            found_dates.append((matches[0], format_desc))
    
    for pattern, format_desc in time_patterns:
        matches = re.findall(pattern, filename)
        if matches:
            found_times.append((matches[0], format_desc))
    
    if found_dates:
        print("📅 Найденные даты в имени файла:")
        for date_match, format_desc in found_dates:
            print(f"   {' '.join(date_match)} (формат: {format_desc})")
    else:
        print("📅 Дат в имени файла не обнаружено")
    
    if found_times:
        print("⏰ Найденное время в имени файла:")
        for time_match, format_desc in found_times:
            print(f"   {' '.join(time_match)} (формат: {format_desc})")
    else:
        print("⏰ Времени в имени файла не обнаружено")

def show_protocol_preview(file_path: str):
    """Показывает превью того, как будет выглядеть протокол"""
    
    processor = MeetingProcessor("test", "test")
    datetime_info = processor.get_file_datetime_info(file_path)
    
    print(f"\n📋 ПРЕВЬЮ ПРОТОКОЛА:")
    print("=" * 20)
    
    preview = f"""
Дата встречи: {datetime_info['date']}
День недели: {datetime_info['weekday_ru']}
Исходный файл: {Path(file_path).name}

Участники встречи: [будет определено из аудио]

Краткое резюме встречи: [будет создано Claude]

Основные обсуждаемые вопросы: [анализ транскрипта]

Принятые решения: [извлечение из контекста]

Назначенные задачи и ответственные: [определение из речи]

Следующие шаги: [планирование из обсуждения]

---
ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ
- Исходный файл обработан: {datetime_info['datetime_full']}
- День недели: {datetime_info['weekday_ru']}
- Протокол создан автоматически
"""
    
    print(preview)

def main():
    """Основная функция"""
    
    print("📅 АНАЛИЗАТОР ДАТЫ И ВРЕМЕНИ МЕДИАФАЙЛОВ")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = input("📁 Введите путь к файлу: ").strip().strip('"')
    
    if not file_path:
        print("❌ Путь к файлу не указан")
        return
    
    analyze_file_datetime(file_path)
    analyze_filename_patterns(file_path)
    show_protocol_preview(file_path)
    
    print(f"\n💡 КАК ИСПОЛЬЗОВАТЬ:")
    print("=" * 20)
    print("1. Эта информация автоматически добавляется в протокол")
    print("2. Дата и время берутся из метаданных файла")
    print("3. Claude использует эту информацию для контекста")
    print("4. В транскрипте появляется заголовок с датой/временем")
    
    print(f"\n🚀 Запустите обработку:")
    print(f"python meeting_processor.py \"{file_path}\"")

if __name__ == "__main__":
    main()