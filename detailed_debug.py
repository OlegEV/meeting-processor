#!/usr/bin/env python3
"""
Детальная отладка процесса идентификации
"""

import json
from team_identifier import TeamIdentifier

def debug_identification_step_by_step():
    """Пошаговая отладка процесса идентификации"""
    print("🔍 ПОШАГОВАЯ ОТЛАДКА ИДЕНТИФИКАЦИИ")
    print("=" * 60)
    
    # Создаем идентификатор
    identifier = TeamIdentifier()
    
    # Тестовый транскрипт
    test_transcript = "Спикер 0: Влад, как дела?"
    print(f"📝 Тестовый транскрипт: '{test_transcript}'")
    
    # Шаг 1: Проверяем настройки
    print(f"\n1️⃣ НАСТРОЙКИ:")
    print(f"   Идентификация включена: {identifier.identification_enabled}")
    print(f"   Применяется к 'standup': {identifier.should_apply_identification('standup')}")
    print(f"   Порог уверенности: {identifier.config.get('team_identification', {}).get('confidence_threshold', 0.7)}")
    print(f"   Участников загружено: {len(identifier.team_members)}")
    
    # Шаг 2: Извлечение спикеров
    print(f"\n2️⃣ ИЗВЛЕЧЕНИЕ СПИКЕРОВ:")
    speakers = identifier._extract_speakers_from_transcript(test_transcript)
    print(f"   Найдено спикеров: {len(speakers)}")
    for speaker_id, text in speakers.items():
        print(f"   '{speaker_id}': '{text}'")
    
    # Шаг 3: Анализ каждого спикера
    print(f"\n3️⃣ АНАЛИЗ КАЖДОГО СПИКЕРА:")
    
    for speaker_id, speaker_text in speakers.items():
        print(f"\n   Анализируем '{speaker_id}': '{speaker_text}'")
        
        # Проверяем всех участников
        print(f"   Проверка всех участников:")
        best_score = 0
        best_member = None
        
        for member_id, member_info in identifier.team_members.items():
            score = identifier._calculate_match_score(speaker_text, member_info, "standup")
            
            print(f"     {member_id} ({member_info.get('full_name', '')}): {score:.3f}")
            
            if score > best_score:
                best_score = score
                best_member = member_id
        
        threshold = identifier.config.get("team_identification", {}).get("confidence_threshold", 0.7)
        print(f"   → Лучший результат: {best_member} ({best_score:.3f})")
        print(f"   → Превышает порог {threshold}: {'✅' if best_score >= threshold else '❌'}")
        
        # Детальный анализ лучшего кандидата
        if best_member:
            print(f"\n   🔍 ДЕТАЛЬНЫЙ АНАЛИЗ '{best_member}':")
            member_info = identifier.team_members[best_member]
            
            # Проверяем каждую стратегию
            strategies = identifier.config.get("identification_rules", {}).get("matching_strategies", [])
            if not strategies:
                strategies = [
                    {"strategy": "exact_name_match", "weight": 1.0},
                    {"strategy": "alias_match", "weight": 0.9},
                    {"strategy": "voice_keyword_match", "weight": 0.8},
                    {"strategy": "partial_name_match", "weight": 0.7},
                    {"strategy": "role_context_match", "weight": 0.6}
                ]
            
            text_lower = speaker_text.lower()
            total_score = 0.0
            
            for strategy in strategies:
                strategy_name = strategy["strategy"]
                weight = strategy["weight"]
                score = 0.0
                
                print(f"     Стратегия '{strategy_name}' (вес {weight}):")
                
                if strategy_name == "exact_name_match":
                    full_name = member_info.get("full_name", "").lower()
                    if full_name in text_lower:
                        score = 1.0
                    print(f"       Полное имя '{full_name}' в '{text_lower}': {score}")
                
                elif strategy_name == "alias_match":
                    aliases = member_info.get("aliases", [])
                    print(f"       Псевдонимы: {aliases}")
                    for alias in aliases:
                        if alias.lower() in text_lower:
                            score = max(score, 0.9)
                            print(f"         ✅ Найден псевдоним '{alias}' в тексте")
                    if score == 0:
                        print(f"         ❌ Псевдонимы не найдены в '{text_lower}'")
                
                elif strategy_name == "voice_keyword_match":
                    keywords = member_info.get("voice_keywords", [])
                    print(f"       Ключевые слова: {keywords}")
                    for keyword in keywords:
                        if keyword in text_lower:
                            score = max(score, 0.8)
                            print(f"         ✅ Найдено ключевое слово '{keyword}' в тексте")
                    if score == 0:
                        print(f"         ❌ Ключевые слова не найдены в '{text_lower}'")
                
                elif strategy_name == "partial_name_match":
                    search_terms = member_info.get("search_terms", [])
                    print(f"       Поисковые термины: {search_terms[:5]}...")  # Показываем первые 5
                    
                    try:
                        from fuzzywuzzy import fuzz
                        for term in search_terms:
                            if len(term) > 2:
                                fuzzy_score = fuzz.partial_ratio(term, text_lower) / 100.0
                                if fuzzy_score > 0.8:
                                    score = max(score, fuzzy_score * 0.7)
                                    print(f"         ✅ Нечеткое совпадение '{term}': {fuzzy_score:.3f}")
                                    break
                    except ImportError:
                        for term in search_terms:
                            if len(term) > 2 and term in text_lower:
                                score = max(score, 0.7)
                                print(f"         ✅ Точное совпадение термина '{term}'")
                                break
                    
                    if score == 0:
                        print(f"         ❌ Поисковые термины не найдены")
                
                elif strategy_name == "role_context_match":
                    context_score = identifier._check_role_context(text_lower, member_info, "standup")
                    score = context_score
                    print(f"       Контекст роли: {score:.3f}")
                
                weighted_score = score * weight
                total_score += weighted_score
                print(f"       → Оценка: {score:.3f}, взвешенная: {weighted_score:.3f}")
            
            # Нормализуем итоговую оценку
            max_possible_score = sum(s["weight"] for s in strategies)
            if max_possible_score > 0:
                normalized_score = total_score / max_possible_score
            else:
                normalized_score = 0
            
            print(f"     💯 ИТОГОВЫЙ СЧЕТ:")
            print(f"       Сумма взвешенных оценок: {total_score:.3f}")
            print(f"       Максимально возможный: {max_possible_score:.3f}")
            print(f"       Нормализованный: {normalized_score:.3f}")
            print(f"       Минимум из (нормализованный, 1.0): {min(normalized_score, 1.0):.3f}")

def test_manual_fixes():
    """Тестирует ручные исправления"""
    print(f"\n4️⃣ ТЕСТИРОВАНИЕ РУЧНЫХ ИСПРАВЛЕНИЙ:")
    
    # Простые тесты для проверки разных вариантов
    test_cases = [
        "влад",
        "Влад", 
        "владислав",
        "Владислав",
        "vlad"
    ]
    
    identifier = TeamIdentifier()
    
    for test_word in test_cases:
        test_transcript = f"Спикер 0: {test_word}, как дела?"
        print(f"\n   Тест: '{test_transcript}'")
        
        result = identifier.identify_participants(test_transcript, "standup")
        
        if result.get("identified") and result.get("speakers"):
            speaker_info = list(result["speakers"].values())[0]
            name = speaker_info.get("full_name", "Unknown")
            confidence = list(result["confidence_scores"].values())[0]
            print(f"     ✅ Найден: {name} (уверенность: {confidence:.0%})")
        else:
            print(f"     ❌ Не найден")

def suggest_immediate_fixes():
    """Предлагает немедленные исправления"""
    print(f"\n5️⃣ ПРЕДЛОЖЕНИЯ НЕМЕДЛЕННЫХ ИСПРАВЛЕНИЙ:")
    
    identifier = TeamIdentifier()
    
    # Проверяем конкретно участника с именем Владислав
    vlad_member = None
    for member_id, member_info in identifier.team_members.items():
        if "владислав" in member_info.get("full_name", "").lower():
            vlad_member = (member_id, member_info)
            break
    
    if vlad_member:
        member_id, member_info = vlad_member
        print(f"   Найден участник: {member_info.get('full_name')}")
        print(f"   ID: {member_id}")
        print(f"   Псевдонимы: {member_info.get('aliases', [])}")
        print(f"   Ключевые слова: {member_info.get('voice_keywords', [])}")
        
        # Проверяем, есть ли "влад" в псевдонимах
        aliases = [alias.lower() for alias in member_info.get('aliases', [])]
        if "влад" not in aliases:
            print(f"   ❌ 'влад' отсутствует в псевдонимах!")
            print(f"   💡 Добавьте 'влад' в aliases для {member_info.get('full_name')}")
        else:
            print(f"   ✅ 'влад' найден в псевдонимах")
        
        # Проверяем ключевые слова
        keywords = [kw.lower() for kw in member_info.get('voice_keywords', [])]
        if "влад" not in keywords:
            print(f"   ❌ 'влад' отсутствует в ключевых словах!")
            print(f"   💡 Добавьте 'влад' в voice_keywords для {member_info.get('full_name')}")
        else:
            print(f"   ✅ 'влад' найден в ключевых словах")
    
    print(f"\n   🔧 РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:")
    print(f"   1. Убедитесь, что 'влад' есть в aliases И voice_keywords")
    print(f"   2. Снизьте порог уверенности до 0.3-0.4")
    print(f"   3. Установите fuzzywuzzy: pip install fuzzywuzzy")
    print(f"   4. Проверьте регистр букв в псевдонимах")

def main():
    """Главная функция отладки"""
    debug_identification_step_by_step()
    test_manual_fixes()
    suggest_immediate_fixes()

if __name__ == "__main__":
    main()
