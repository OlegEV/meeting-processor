#!/usr/bin/env python3
"""
Демонстрационная версия веб-приложения с тестовыми данными
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Импортируем основное приложение
from run_web import WorkingMeetingWebApp

class DemoMeetingWebApp(WorkingMeetingWebApp):
    """Демо-версия с предзагруженными тестовыми данными"""
    
    def __init__(self, config_file: str = "config.json"):
        super().__init__(config_file)
        self.add_demo_data()
    
    def add_demo_data(self):
        """Добавляет демонстрационные данные"""
        
        # Создаем тестовую задачу
        test_job_id = "demo-job-123"
        
        # Убеждаемся, что файлы существуют
        transcript_path = Path('web_output/test-job-123/test_meeting_transcript.txt')
        summary_path = Path('web_output/test-job-123/test_meeting_summary.md')
        
        if not transcript_path.exists() or not summary_path.exists():
            print("⚠️ Тестовые файлы не найдены, создаем их...")
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Создаем тестовый транскрипт
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write("""ТРАНСКРИПТ ВСТРЕЧИ

Дата: 2025-06-03
Время: 12:30

Speaker 1: Добро пожаловать на нашу еженедельную встречу по проекту. Сегодня мы обсудим прогресс по основным задачам.

Speaker 2: Спасибо. Я хотел бы начать с отчета о разработке. На этой неделе мы завершили интеграцию API и начали тестирование.

Speaker 1: Отлично. Какие есть проблемы или блокеры?

Speaker 2: Основная проблема - это производительность базы данных. Запросы выполняются медленнее ожидаемого.

Speaker 3: По этому поводу - я уже начал оптимизацию индексов. Планирую завершить к пятнице.

Speaker 1: Хорошо. Что по маркетинговой кампании?

Speaker 4: Мы запустили A/B тестирование новых креативов. Первые результаты показывают увеличение конверсии на 15%.

Speaker 1: Превосходно. Какие следующие шаги?

Speaker 2: Нужно завершить тестирование API к среде, затем можем переходить к релизу.

Speaker 3: Оптимизация БД будет готова к пятнице, как я сказал.

Speaker 4: Продолжим A/B тест еще неделю, затем примем решение о масштабировании.

Speaker 1: Отлично. Встретимся на следующей неделе в то же время. Спасибо всем.
""")
            
            # Создаем тестовый протокол
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write("""# ПРОТОКОЛ ВСТРЕЧИ

## Общая информация
- **Дата:** 03.06.2025
- **Время:** 12:30
- **Тип:** Еженедельная встреча по проекту
- **Шаблон:** Standard

## Участники
- Speaker 1 - Руководитель проекта
- Speaker 2 - Разработчик
- Speaker 3 - Администратор БД
- Speaker 4 - Маркетолог

## Основные темы

### Разработка
- ✅ Завершена интеграция API
- 🔄 Начато тестирование
- ⚠️ Проблема с производительностью БД

### Маркетинг
- ✅ Запущено A/B тестирование
- 📈 Увеличение конверсии на 15%

## Задачи
- **Speaker 2:** Завершить тестирование API к среде
- **Speaker 3:** Оптимизация БД до пятницы
- **Speaker 4:** Продолжить A/B тест еще неделю

## Следующая встреча
Следующая неделя, то же время
""")
        
        # Добавляем задачу в память приложения
        with self.jobs_lock:
            self.processing_jobs[test_job_id] = {
                'status': 'completed',
                'filename': 'demo_meeting.mp3',
                'template': 'standard',
                'file_path': 'web_uploads/demo_meeting.mp3',
                'created_at': datetime.now(),
                'progress': 100,
                'message': 'Обработка завершена успешно!',
                'transcript_file': str(transcript_path.absolute()),
                'summary_file': str(summary_path.absolute()),
                'completed_at': datetime.now()
            }
        
        print(f"✅ Демо-задача {test_job_id} добавлена")
        print(f"📄 Транскрипт: {transcript_path}")
        print(f"📋 Протокол: {summary_path}")

def main():
    """Основная функция для демо"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Демо веб-интерфейс с тестовыми данными")
    parser.add_argument("-c", "--config", default="config.json", help="Путь к файлу конфигурации")
    parser.add_argument("--host", default="127.0.0.1", help="IP адрес для запуска сервера")
    parser.add_argument("--port", type=int, default=5002, help="Порт для запуска сервера")
    parser.add_argument("--debug", action="store_true", help="Запуск в режиме отладки")
    
    args = parser.parse_args()
    
    try:
        # Создаем демо веб-приложение
        demo_app = DemoMeetingWebApp(args.config)
        
        print("\n" + "="*60)
        print("🚀 MEETING PROCESSOR DEMO WEB SERVER")
        print("="*60)
        print(f"📱 Веб-интерфейс: http://localhost:{args.port}")
        print("🎯 Демо с тестовыми данными")
        print("🔧 Новый функционал: генерация протоколов в разных шаблонах")
        print("\n💡 Для остановки нажмите Ctrl+C")
        print("="*60)
        
        # Запускаем сервер
        demo_app.run(host=args.host, port=args.port, debug=args.debug)
        
    except KeyboardInterrupt:
        print("\n👋 Демо-приложение остановлено")
    except Exception as e:
        print(f"❌ Ошибка запуска демо-приложения: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
