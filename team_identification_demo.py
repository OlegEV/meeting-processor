#!/usr/bin/env python3
"""
Демонстрация идентификации участников команды
ИСПРАВЛЕННАЯ ВЕРСИЯ - устранены ошибки в подсчете участников
"""

import sys
import os
from pathlib import Path

try:
    from team_identifier import TeamIdentifier
except ImportError:
    print("❌ Модуль team_identifier.py не найден!")
    sys.exit(1)

def demo_standup_meeting():
    """Демонстрация идентификации на стендапе"""
    print("🎯 ДЕМОНСТРАЦИЯ: Ежедневный стендап")
    print("=" * 50)
    
    # Тестовый транскрипт стендапа
    standup_transcript = """
Спикер 0: Доброе утро, команда! Начинаем наш ежедневный стендап. Влад, как дела с новой авторизацией?

Спикер 1: Привет всем! Вчера закончил интеграцию OAuth, сегодня планирую заняться тестированием API endpoints. Блокеров нет, все идет по плану.

Спикер 2: Отлично, Владислав. Юля, как обстоят дела с тестированием релиза?

Спикер 3: Вчера прогнала автоматические тесты на новом билде, нашла два критических бага в модуле платежей. Саша сегодня поможет с регрессионным тестированием.

Спикер 4: Да, помогу Юле с тестами. У меня вчера была работа с performance тестированием, все прошло гладко.

Спикер 5: Отлично! Герман, что у нас с требованиями к новой фиче?

Спикер 6: Документация почти готова, осталось согласовать mockup с дизайнером. Елена поможет с пользовательскими сценариями.

Спикер 7: Да, Герман, я уже начала работу над user story для новой функциональности.
"""
    
    identifier = TeamIdentifier()
    
    if not identifier.identification_enabled:
        print("❌ Идентификация отключена в конфигурации")
        return
    
    print("📝 Исходный транскрипт:")
    print(standup_transcript[:300] + "...\n")
    
    # Идентифицируем участников
    result = identifier.identify_participants(standup_transcript, "standup")
    
    if result["identified"]:
        print("✅ РЕЗУЛЬТАТЫ ИДЕНТИФИКАЦИИ")
        print(f"Участников определено: {result['statistics']['total_identified']}")
        print(f"Команды: {', '.join(result['statistics']['teams_present'])}")
        
        print("\n👥 УЧАСТНИКИ ВСТРЕЧИ:")
        print(result["participant_summary"])
        
        print("\n🔄 ЗАМЕНЫ СПИКЕРОВ:")
        for old, new in result["replacements"].items():
            confidence = result["confidence_scores"].get(old, 0)
            print(f"   {old} → {new} (точность: {confidence:.0%})")
        
        # Показываем модифицированный транскрипт
        modified_transcript = identifier.apply_speaker_replacements(standup_transcript, "standup")
        print("\n📝 МОДИФИЦИРОВАННЫЙ ТРАНСКРИПТ:")
        print(modified_transcript[:400] + "...")
        
    else:
        print("❌ Идентификация не удалась")
        print(f"Причина: {result.get('reason', 'неизвестно')}")

def demo_project_meeting():
    """Демонстрация идентификации на проектной встрече"""
    print("\n🎯 ДЕМОНСТРАЦИЯ: Проектная встреча")
    print("=" * 50)
    
    project_transcript = """
Спикер 0: Добро пожаловать на встречу по проекту. Обсудим текущий статус и планы. Владислав, расскажи о прогрессе разработки.

Спикер 1: Спасибо, Олег. Команда разработки завершила 80% запланированных задач. Основные компоненты готовы, осталась интеграция.

Спикер 2: Отлично! Юлия, как идет тестирование новых модулей?

Спикер 3: Мы протестировали большую часть функционала. Нашли несколько багов средней критичности, но в целом качество хорошее.

Спикер 4: Герман, готовы ли обновленные требования?

Спикер 5: Да, все требования согласованы с заказчиком. Документация обновлена, можно приступать к следующему этапу.
"""
    
    identifier = TeamIdentifier()
    result = identifier.identify_participants(project_transcript, "project")
    
    if result["identified"]:
        print("✅ РЕЗУЛЬТАТЫ ИДЕНТИФИКАЦИИ")
        print(f"Участников определено: {result['statistics']['total_identified']}")
        
        print("\n👥 УЧАСТНИКИ ВСТРЕЧИ:")
        print(result["participant_summary"])
        
        # Показываем контекст команды для шаблона
        team_context = identifier.get_team_context_for_template("project", result["speakers"])
        print("\n📋 КОНТЕКСТ КОМАНДЫ ДЛЯ ШАБЛОНА:")
        print(team_context)
        
    else:
        print("❌ Идентификация не удалась")

def demo_configuration():
    """Демонстрация настроек конфигурации - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    print("\n🎯 ДЕМОНСТРАЦИЯ: Настройки конфигурации")
    print("=" * 50)
    
    identifier = TeamIdentifier()
    
    print("📋 ТЕКУЩИЕ НАСТРОЙКИ:")
    print(f"Идентификация включена: {'✅' if identifier.identification_enabled else '❌'}")
    
    config = identifier.config
    team_config = config.get("team_identification", {})
    
    print(f"Применяется к шаблонам: {', '.join(team_config.get('apply_to_templates', ['все']))}")
    print(f"Порог уверенности: {team_config.get('confidence_threshold', 0.7)}")
    print(f"Нечеткое сравнение: {'✅' if team_config.get('fuzzy_matching', True) else '❌'}")
    
    print(f"\n👥 УЧАСТНИКИ КОМАНДЫ:")
    
    # ИСПРАВЛЕНИЕ: Используем метод get_team_statistics() из TeamIdentifier
    team_stats = identifier.get_team_statistics()
    
    for team_name, member_count in team_stats["teams"].items():
        team_display = {
            "management": "Руководство",
            "development": "Разработка",
            "testing": "Тестирование", 
            "analytics": "Аналитика"
        }.get(team_name, team_name.title())
        
        print(f"   {team_display}: {member_count} чел.")
    
    print(f"   Всего в базе: {team_stats['total_members']} участников")
    
    print(f"\n🔍 СТРАТЕГИИ СОПОСТАВЛЕНИЯ:")
    strategies = config.get("identification_rules", {}).get("matching_strategies", [])
    if strategies:
        for strategy in strategies:
            print(f"   {strategy['strategy']}: вес {strategy['weight']}")
    else:
        print("   Используются стратегии по умолчанию")

def demo_accuracy_test():
    """Тестирование точности идентификации"""
    print("\n🎯 ДЕМОНСТРАЦИЯ: Тест точности идентификации")
    print("=" * 50)
    
    # Тестовые случаи с известными результатами
    test_cases = [
        {
            "name": "Прямое упоминание имени",
            "text": "Спикер 0: Владислав, как дела с задачей?",
            "expected": "Ульянов Владислав"
        },
        {
            "name": "Упоминание сокращенного имени",
            "text": "Спикер 1: Влад работает над новой фичей",
            "expected": "Ульянов Владислав"
        },
        {
            "name": "Контекст разработки",
            "text": "Спикер 2: Вчера закоммитил новый код, сегодня буду тестировать API",
            "expected": "разработка"
        },
        {
            "name": "Контекст тестирования",
            "text": "Спикер 3: Нашла баг в автотестах, нужно исправить регрессию",
            "expected": "тестирование"
        },
        {
            "name": "Упоминание роли",
            "text": "Спикер 4: Как тимлид, я думаю нужно пересмотреть приоритеты",
            "expected": "Team Lead"
        }
    ]
    
    identifier = TeamIdentifier()
    
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    correct_predictions = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Текст: '{test_case['text'][:50]}...'")
        
        # Пытаемся идентифицировать
        result = identifier.identify_participants(test_case['text'], "standup")
        
        if result["identified"] and result["speakers"]:
            speaker_info = list(result["speakers"].values())[0]
            predicted = speaker_info.get("full_name", "неизвестно")
            team_name = speaker_info.get("team_name", "неизвестно")
            confidence = list(result["confidence_scores"].values())[0]
            
            print(f"   Предсказание: {predicted} (команда: {team_name}, точность: {confidence:.0%})")
            
            # Проверяем правильность
            expected_lower = test_case['expected'].lower()
            if (expected_lower in predicted.lower() or 
                expected_lower in speaker_info.get('role', '').lower() or
                expected_lower in team_name.lower()):
                print(f"   Результат: ✅ Правильно")
                correct_predictions += 1
            else:
                print(f"   Результат: ❌ Неправильно (ожидалось: {test_case['expected']})")
        else:
            print(f"   Предсказание: не определено")
            print(f"   Результат: ❌ Не идентифицировано")
    
    accuracy = correct_predictions / len(test_cases) * 100
    print(f"\n📈 ОБЩАЯ ТОЧНОСТЬ: {accuracy:.0f}% ({correct_predictions}/{len(test_cases)})")

def demo_template_application():
    """Демонстрация применения к разным шаблонам"""
    print("\n🎯 ДЕМОНСТРАЦИЯ: Применение к шаблонам")
    print("=" * 50)
    
    identifier = TeamIdentifier()
    
    templates_to_test = ["standup", "project", "business", "review", "standard"]
    
    print("📋 ПРИМЕНЕНИЕ ИДЕНТИФИКАЦИИ ПО ШАБЛОНАМ:")
    
    for template in templates_to_test:
        should_apply = identifier.should_apply_identification(template)
        status = "✅ Применяется" if should_apply else "❌ Не применяется"
        print(f"   {template:12} - {status}")
    
    # Показываем настройки
    apply_to_templates = identifier.config.get("team_identification", {}).get("apply_to_templates", [])
    if apply_to_templates:
        print(f"\n⚙️ Настройка 'apply_to_templates': {', '.join(apply_to_templates)}")
    else:
        print(f"\n⚙️ Настройка 'apply_to_templates': пуста (применяется ко всем)")

def demo_team_statistics():
    """Демонстрация детальной статистики команды"""
    print("\n🎯 ДЕМОНСТРАЦИЯ: Детальная статистика команды")
    print("=" * 50)
    
    identifier = TeamIdentifier()
    
    if not identifier.team_members:
        print("❌ Конфигурация команды не загружена")
        return
    
    team_stats = identifier.get_team_statistics()
    
    print(f"📊 ПОЛНАЯ СТАТИСТИКА:")
    print(f"Общее количество участников: {team_stats['total_members']}")
    print(f"Количество команд: {len(team_stats['teams'])}")
    
    print(f"\n👥 РАЗБИВКА ПО КОМАНДАМ:")
    for team_name, member_ids in team_stats["team_breakdown"].items():
        team_display = {
            "management": "Руководство",
            "development": "Разработка",
            "testing": "Тестирование", 
            "analytics": "Аналитика"
        }.get(team_name, team_name.title())
        
        print(f"\n**{team_display} ({len(member_ids)} чел.):**")
        
        # Показываем участников команды
        for member_id in member_ids[:5]:  # Показываем первых 5
            member_info = identifier.team_members.get(member_id, {})
            full_name = member_info.get("full_name", "Неизвестно")
            role = member_info.get("role", "Роль не указана")
            print(f"   • {full_name} - {role}")
        
        if len(member_ids) > 5:
            print(f"   • ... и еще {len(member_ids) - 5} участников")

def main():
    """Главная функция демонстрации"""
    print("👥 ДЕМОНСТРАЦИЯ ИДЕНТИФИКАЦИИ УЧАСТНИКОВ КОМАНДЫ")
    print("=" * 60)
    
    # Проверяем наличие конфигурации
    if not os.path.exists("team_config.json"):
        print("❌ Файл team_config.json не найден!")
        print("💡 Создайте конфигурацию или запустите:")
        print("   python test_runner.py  # создаст образец конфигурации")
        return
    
    try:
        # Запускаем демонстрации
        demo_standup_meeting()
        demo_project_meeting()
        demo_configuration()
        demo_team_statistics()
        demo_accuracy_test()
        demo_template_application()
        
        print("\n" + "=" * 60)
        print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
        print("=" * 60)
        
        print("\n💡 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Настройте team_config.json под вашу команду")
        print("2. Запустите валидацию: python config_validator.py")
        print("3. Запустите тесты: python test_runner.py")
        print("4. Используйте в production: python meeting_processor.py --template standup --team-id")
        
    except Exception as e:
        print(f"\n❌ Ошибка в демонстрации: {e}")
        import traceback
        traceback.print_exc()
        
        print(f"\n🔧 ВОЗМОЖНЫЕ РЕШЕНИЯ:")
        print("1. Проверьте корректность team_config.json")
        print("2. Убедитесь, что установлен fuzzywuzzy: pip install fuzzywuzzy")
        print("3. Запустите валидацию: python config_validator.py")

if __name__ == "__main__":
    main()
