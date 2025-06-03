#!/usr/bin/env python3
"""
Утилита для управления шаблонами протоколов встреч
"""

import os
import sys
from pathlib import Path

try:
    from meeting_templates import MeetingTemplates
except ImportError:
    print("❌ Файл meeting_templates.py не найден!")
    sys.exit(1)

def show_available_templates():
    """Показывает все доступные шаблоны"""
    print("📝 ДОСТУПНЫЕ ШАБЛОНЫ ПРОТОКОЛОВ")
    print("=" * 50)
    
    templates = MeetingTemplates()
    available = templates.get_available_templates()
    
    print("🏗️ ВСТРОЕННЫЕ ШАБЛОНЫ:")
    for template_name in available['builtin']:
        if hasattr(templates, 'config') and 'template_descriptions' in templates.config:
            description = templates.config['template_descriptions'].get(template_name, "Описание недоступно")
            print(f"   📋 {template_name:12} - {description}")
        else:
            print(f"   📋 {template_name}")
    
    if available['custom']:
        print("\n👤 ПОЛЬЗОВАТЕЛЬСКИЕ ШАБЛОНЫ:")
        for template_name in available['custom']:
            print(f"   📋 {template_name}")
    else:
        print("\n👤 Пользовательских шаблонов пока нет")

def preview_template():
    """Показывает превью шаблона"""
    templates = MeetingTemplates()
    available = templates.get_available_templates()
    
    print("📖 ПРЕВЬЮ ШАБЛОНА")
    print("=" * 30)
    
    template_name = input("Введите название шаблона: ").strip()
    
    if template_name not in available['all']:
        print(f"❌ Шаблон '{template_name}' не найден")
        return
    
    try:
        # Получаем шаблон с тестовыми данными
        import datetime
        test_datetime_info = {
            'date': '27.05.2025',
            'time': '14:30:00',
            'datetime_full': '27.05.2025 14:30:00',
            'weekday_ru': 'вторник'
        }
        
        template = templates.get_template(template_name, "Тестовый транскрипт встречи...", test_datetime_info)
        
        print(f"\n📝 Шаблон '{template_name}':")
        print("-" * 50)
        
        # Показываем первые 800 символов
        preview = template[:800]
        if len(template) > 800:
            preview += "\n\n... [обрезано для превью] ..."
        
        print(preview)
        
    except Exception as e:
        print(f"❌ Ошибка при получении шаблона: {e}")

def create_custom_template():
    """Создает пользовательский шаблон"""
    print("✨ СОЗДАНИЕ ПОЛЬЗОВАТЕЛЬСКОГО ШАБЛОНА")
    print("=" * 45)
    
    templates = MeetingTemplates()
    
    name = input("Название нового шаблона: ").strip()
    if not name:
        print("❌ Название не может быть пустым")
        return
    
    print(f"\nВведите шаблон для '{name}':")
    print("📝 Доступные переменные:")
    print("   {datetime_info} - информация о дате/времени")
    print("   {datetime_display} - отформатированная дата")
    print("   {transcript} - транскрипт встречи")
    print("\n💡 Завершите ввод пустой строкой:")
    
    lines = []
    while True:
        try:
            line = input()
            if not line:
                break
            lines.append(line)
        except EOFError:
            break
    
    if not lines:
        print("❌ Шаблон не может быть пустым")
        return
    
    template_text = "\n".join(lines)
    
    try:
        templates.add_custom_template(name, template_text)
        print(f"✅ Шаблон '{name}' успешно создан!")
    except Exception as e:
        print(f"❌ Ошибка при создании шаблона: {e}")

def test_auto_detection():
    """Тестирует автоматическое определение типа встречи"""
    print("🤖 ТЕСТ АВТООПРЕДЕЛЕНИЯ ТИПА ВСТРЕЧИ")
    print("=" * 40)
    
    templates = MeetingTemplates()
    
    print("Введите тестовый текст транскрипта:")
    print("(например: 'вчера я делал задачу по проекту, сегодня планирую заняться багом')")
    
    test_text = input("Текст: ").strip()
    
    if not test_text:
        # Примеры для тестирования
        test_cases = [
            ("вчера я делал задачу по проекту, сегодня планирую заняться багом, есть блокеры", "standup"),
            ("обсуждаем архитектуру системы, нужно исправить баги в API", "technical"),
            ("клиент хочет увеличить бюджет, обсуждаем ROI и прибыль", "business"),
            ("мозговой штурм новых идей для продукта, креативные предложения", "brainstorm"),
            ("что прошло хорошо в спринте, какие проблемы нужно улучшить", "review")
        ]
        
        print("\n🧪 Тестирование на примерах:")
        for text, expected in test_cases:
            detected = templates._detect_meeting_type(text)
            status = "✅" if detected == expected else "❌"
            print(f"{status} '{text[:50]}...' -> {detected} (ожидалось: {expected})")
    else:
        detected_type = templates._detect_meeting_type(test_text)
        print(f"\n🎯 Определенный тип: {detected_type}")

def template_statistics():
    """Показывает статистику по шаблонам"""
    print("📊 СТАТИСТИКА ШАБЛОНОВ")
    print("=" * 30)
    
    templates = MeetingTemplates()
    available = templates.get_available_templates()
    
    print(f"🏗️ Встроенных шаблонов: {len(available['builtin'])}")
    print(f"👤 Пользовательских шаблонов: {len(available['custom'])}")
    print(f"📝 Всего доступно: {len(available['all'])}")
    
    # Показываем конфигурацию
    if hasattr(templates, 'config'):
        config = templates.config
        print(f"\n⚙️ НАСТРОЙКИ:")
        print(f"   📋 Шаблон по умолчанию: {config.get('default_template', 'не указан')}")
        
        settings = config.get('template_settings', {})
        print(f"   🤖 Автоопределение типа: {'Да' if settings.get('auto_detect_meeting_type', False) else 'Нет'}")
        print(f"   📅 Включать дату файла: {'Да' if settings.get('include_file_datetime', True) else 'Нет'}")
        print(f"   🔧 Включать техническую информацию: {'Да' if settings.get('include_technical_info', True) else 'Нет'}")
        print(f"   🎯 Максимум токенов: {settings.get('max_tokens', 2000)}")

def export_template():
    """Экспортирует шаблон в файл"""
    print("📤 ЭКСПОРТ ШАБЛОНА")
    print("=" * 25)
    
    templates = MeetingTemplates()
    available = templates.get_available_templates()
    
    template_name = input("Название шаблона для экспорта: ").strip()
    
    if template_name not in available['all']:
        print(f"❌ Шаблон '{template_name}' не найден")
        return
    
    output_file = input(f"Имя файла для сохранения (по умолчанию: {template_name}_template.txt): ").strip()
    if not output_file:
        output_file = f"{template_name}_template.txt"
    
    try:
        # Получаем шаблон
        if template_name in available['custom']:
            template_content = templates.config['custom_templates'][template_name]
        else:
            # Для встроенных шаблонов получаем исходный код
            template_content = templates.builtin_templates[template_name]()
        
        # Сохраняем в файл
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Шаблон: {template_name}\n")
            f.write(f"# Экспортировано: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(template_content)
        
        print(f"✅ Шаблон '{template_name}' экспортирован в '{output_file}'")
        
    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")

def import_template():
    """Импортирует шаблон из файла"""
    print("📥 ИМПОРТ ШАБЛОНА")
    print("=" * 25)
    
    file_path = input("Путь к файлу шаблона: ").strip().strip('"')
    
    if not os.path.exists(file_path):
        print(f"❌ Файл '{file_path}' не найден")
        return
    
    template_name = input("Название для импортируемого шаблона: ").strip()
    
    if not template_name:
        print("❌ Название не может быть пустым")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Убираем комментарии экспорта, если есть
        lines = content.split('\n')
        template_lines = []
        skip_comments = True
        
        for line in lines:
            if skip_comments and line.startswith('#'):
                continue
            elif skip_comments and line.strip() == '':
                continue
            else:
                skip_comments = False
                template_lines.append(line)
        
        template_content = '\n'.join(template_lines)
        
        templates = MeetingTemplates()
        templates.add_custom_template(template_name, template_content)
        
        print(f"✅ Шаблон '{template_name}' успешно импортирован из '{file_path}'")
        
    except Exception as e:
        print(f"❌ Ошибка при импорте: {e}")

def reset_templates_config():
    """Сбрасывает конфигурацию шаблонов к значениям по умолчанию"""
    print("🔄 СБРОС КОНФИГУРАЦИИ ШАБЛОНОВ")
    print("=" * 40)
    
    confirm = input("⚠️ Это удалит все пользовательские шаблоны! Продолжить? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y', 'да', 'д']:
        print("❌ Операция отменена")
        return
    
    try:
        config_file = "templates_config.json"
        if os.path.exists(config_file):
            os.remove(config_file)
            print(f"🗑️ Файл '{config_file}' удален")
        
        # Создаем новый экземпляр для генерации конфигурации по умолчанию
        templates = MeetingTemplates()
        print("✅ Конфигурация шаблонов сброшена к значениям по умолчанию")
        
    except Exception as e:
        print(f"❌ Ошибка при сбросе конфигурации: {e}")

def main():
    """Основная функция меню"""
    print("📝 МЕНЕДЖЕР ШАБЛОНОВ ПРОТОКОЛОВ ВСТРЕЧ")
    print("=" * 50)
    
    while True:
        print("\n🎯 Выберите действие:")
        print("1. 📋 Показать доступные шаблоны")
        print("2. 📖 Превью шаблона")
        print("3. ✨ Создать пользовательский шаблон")
        print("4. 🤖 Тест автоопределения типа встречи")
        print("5. 📊 Статистика шаблонов")
        print("6. 📤 Экспортировать шаблон")
        print("7. 📥 Импортировать шаблон")
        print("8. 🔄 Сбросить конфигурацию")
        print("9. ❌ Выход")
        
        choice = input("\nВведите номер (1-9): ").strip()
        
        try:
            if choice == "1":
                show_available_templates()
            elif choice == "2":
                preview_template()
            elif choice == "3":
                create_custom_template()
            elif choice == "4":
                test_auto_detection()
            elif choice == "5":
                template_statistics()
            elif choice == "6":
                export_template()
            elif choice == "7":
                import_template()
            elif choice == "8":
                reset_templates_config()
            elif choice == "9":
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Программа прервана пользователем")
            break
        except Exception as e:
            print(f"\n❌ Произошла ошибка: {e}")
            print("💡 Попробуйте еще раз или выберите другое действие")

if __name__ == "__main__":
    main()