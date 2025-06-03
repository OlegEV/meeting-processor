#!/usr/bin/env python3
"""
Диагностический инструмент для выявления проблем идентификации
"""

import json
import os
from team_identifier import TeamIdentifier

def diagnose_identification_issues():
    """Диагностирует проблемы с идентификацией"""
    print("🔍 ДИАГНОСТИКА ПРОБЛЕМ ИДЕНТИФИКАЦИИ")
    print("=" * 60)
    
    # Проверяем конфигурацию
    if not os.path.exists("team_config.json"):
        print("❌ team_config.json не найден!")
        return
    
    identifier = TeamIdentifier()
    
    print("1️⃣ ПРОВЕРКА КОНФИГУРАЦИИ:")
    print(f"   Идентификация включена: {identifier.identification_enabled}")
    print(f"   Участников загружено: {len(identifier.team_members)}")
    
    # Проверяем apply_to_templates
    apply_to_templates = identifier.config.get("team_identification", {}).get("apply_to_templates", [])
    print(f"   Применяется к шаблонам: {apply_to_templates}")
    print(f"   Применится к 'standup': {identifier.should_apply_identification('standup')}")
    
    # Проверяем порог уверенности
    threshold = identifier.config.get("team_identification", {}).get("confidence_threshold", 0.7)
    print(f"   Порог уверенности: {threshold}")
    
    print("\n2️⃣ УЧАСТНИКИ КОМАНДЫ:")
    for member_id, member_info in list(identifier.team_members.items())[:3]:  # Первые 3
        print(f"   {member_id}:")
        print(f"     Полное имя: '{member_info.get('full_name', '')}'")
        print(f"     Псевдонимы: {member_info.get('aliases', [])}")
        print(f"     Ключевые слова: {member_info.get('voice_keywords', [])}")
        print(f"     Поисковые термины: {member_info.get('search_terms', [])}")
    
    print("\n3️⃣ ТЕСТИРОВАНИЕ ПОИСКА:")
    test_phrases = [
        "Влад",
        "Владислав", 
        "Ульянов",
        "влад",
        "владислав"
    ]
    
    for phrase in test_phrases:
        print(f"\n   Тестируем фразу: '{phrase}'")
        found_matches = []
        
        for member_id, member_info in identifier.team_members.items():
            # Проверяем точное совпадение с именем
            full_name = member_info.get("full_name", "").lower()
            if phrase.lower() in full_name:
                found_matches.append(f"{member_id} (полное имя)")
            
            # Проверяем псевдонимы
            aliases = member_info.get("aliases", [])
            for alias in aliases:
                if phrase.lower() == alias.lower():
                    found_matches.append(f"{member_id} (псевдоним: {alias})")
            
            # Проверяем ключевые слова
            keywords = member_info.get("voice_keywords", [])
            for keyword in keywords:
                if phrase.lower() == keyword.lower():
                    found_matches.append(f"{member_id} (ключевое слово: {keyword})")
        
        if found_matches:
            print(f"     ✅ Найдены совпадения: {', '.join(found_matches)}")
        else:
            print(f"     ❌ Совпадений не найдено")
    
    print("\n4️⃣ ТЕСТИРОВАНИЕ ПОЛНОЙ ИДЕНТИФИКАЦИИ:")
    test_transcript = "Спикер 0: Влад, как дела?"
    print(f"   Тестовый транскрипт: '{test_transcript}'")
    
    # Извлекаем спикеров
    speakers = identifier._extract_speakers_from_transcript(test_transcript)
    print(f"   Извлеченные спикеры: {speakers}")
    
    # Пробуем идентификацию с низким порогом
    print(f"\n   Понижаем порог уверенности до 0.1...")
    original_threshold = identifier.config.get("team_identification", {}).get("confidence_threshold", 0.7)
    identifier.config["team_identification"]["confidence_threshold"] = 0.1
    
    result = identifier.identify_participants(test_transcript, "standup")
    print(f"   Результат с низким порогом:")
    print(f"     Идентифицировано: {result.get('identified', False)}")
    print(f"     Спикеров найдено: {len(result.get('speakers', {}))}")
    
    # Показываем детали для каждого спикера
    for speaker_id, speaker_text in speakers.items():
        print(f"\n   Анализ '{speaker_id}': '{speaker_text}'")
        
        best_score = 0
        best_member = None
        
        for member_id, member_info in identifier.team_members.items():
            score = identifier._calculate_match_score(speaker_text, member_info, "standup")
            print(f"     {member_id}: {score:.3f}")
            
            if score > best_score:
                best_score = score
                best_member = member_id
        
        print(f"     → Лучшее совпадение: {best_member} ({best_score:.3f})")
        print(f"     → Превышает порог {original_threshold}: {'✅' if best_score >= original_threshold else '❌'}")
    
    # Восстанавливаем исходный порог
    identifier.config["team_identification"]["confidence_threshold"] = original_threshold
    
    print("\n5️⃣ РЕКОМЕНДАЦИИ:")
    if len(identifier.team_members) == 0:
        print("   ❌ Участники команды не загружены - проверьте team_config.json")
    elif not identifier.identification_enabled:
        print("   ❌ Идентификация отключена - установите 'enabled': true")
    elif not identifier.should_apply_identification('standup'):
        print("   ❌ Идентификация не применяется к шаблону 'standup'")
        print("      Добавьте 'standup' в 'apply_to_templates' или оставьте массив пустым")
    elif threshold > 0.8:
        print("   ⚠️ Слишком высокий порог уверенности - попробуйте снизить до 0.6-0.7")
    else:
        print("   💡 Возможные решения:")
        print("      1. Снизьте порог уверенности до 0.5-0.6")
        print("      2. Добавьте больше псевдонимов для участников")
        print("      3. Проверьте, что имена в конфигурации соответствуют транскрипту")
        print("      4. Установите fuzzywuzzy для лучшего поиска: pip install fuzzywuzzy")

def suggest_config_improvements():
    """Предлагает улучшения конфигурации"""
    print("\n6️⃣ ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ КОНФИГУРАЦИИ:")
    
    if not os.path.exists("team_config.json"):
        return
    
    with open("team_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    team_members = config.get("team_members", {})
    
    for team_name, members in team_members.items():
        for member_id, member_info in members.items():
            full_name = member_info.get("full_name", "")
            aliases = member_info.get("aliases", [])
            keywords = member_info.get("voice_keywords", [])
            
            suggestions = []
            
            # Проверяем наличие коротких псевдонимов
            if full_name:
                name_parts = full_name.split()
                for part in name_parts:
                    if len(part) > 2 and part not in aliases:
                        suggestions.append(f"добавить псевдоним '{part}'")
            
            # Проверяем ключевые слова
            if not keywords:
                suggestions.append("добавить voice_keywords")
            
            if suggestions:
                print(f"   {member_id} ({full_name}):")
                for suggestion in suggestions:
                    print(f"     • {suggestion}")

def create_test_config():
    """Создает тестовую конфигурацию с более простыми именами"""
    test_config = {
        "team_identification": {
            "enabled": True,
            "apply_to_templates": ["standup", "project", "review"],
            "confidence_threshold": 0.5,  # Пониженный порог
            "fuzzy_matching": True,
            "partial_name_matching": True
        },
        "team_members": {
            "development": {
                "vlad": {
                    "full_name": "Владислав",
                    "role": "Developer",
                    "team": "development",
                    "aliases": ["Влад", "Владислав", "влад", "владислав"],
                    "voice_keywords": ["влад", "владислав", "vlad"]
                },
                "sasha": {
                    "full_name": "Александр",
                    "role": "Developer", 
                    "team": "development",
                    "aliases": ["Саша", "Александр", "саша", "александр"],
                    "voice_keywords": ["саша", "александр", "sasha"]
                }
            },
            "testing": {
                "yulia": {
                    "full_name": "Юлия",
                    "role": "QA",
                    "team": "testing",
                    "aliases": ["Юля", "Юлия", "юля", "юлия"],
                    "voice_keywords": ["юля", "юлия", "yulia"]
                }
            }
        }
    }
    
    with open("test_config.json", "w", encoding="utf-8") as f:
        json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    print(f"\n7️⃣ СОЗДАНА ТЕСТОВАЯ КОНФИГУРАЦИЯ:")
    print("   Файл: test_config.json")
    print("   Особенности:")
    print("     • Пониженный порог уверенности (0.5)")
    print("     • Упрощенные имена")
    print("     • Больше псевдонимов")
    print("     • Дублирование в разных регистрах")
    print("\n   Для тестирования:")
    print("   python -c \"from team_identifier import TeamIdentifier; t=TeamIdentifier('test_config.json'); print(t.identify_participants('Спикер 0: Влад, как дела?', 'standup'))\"")

def main():
    """Главная функция диагностики"""
    diagnose_identification_issues()
    suggest_config_improvements()
    create_test_config()
    
    print(f"\n🎯 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Проанализируйте вывод диагностики")
    print("2. Внесите рекомендуемые изменения в team_config.json")
    print("3. Протестируйте с test_config.json")
    print("4. Запустите team_identifier.py повторно")

if __name__ == "__main__":
    main()
