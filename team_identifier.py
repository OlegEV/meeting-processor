#!/usr/bin/env python3
"""
Модуль для идентификации участников команды в транскрипте встречи
ИСПРАВЛЕННАЯ ВЕРСИЯ без синтаксических ошибок
"""

import json
import re
import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

try:
    from fuzzywuzzy import fuzz
except ImportError:
    print("⚠️ fuzzywuzzy не установлен. Установите: pip install fuzzywuzzy")
    print("Будет использоваться упрощенное сравнение строк")
    fuzz = None

class TeamIdentifier:
    """Класс для определения участников встречи по списку команды"""
    
    def __init__(self, config_file: str = "team_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.team_members = self._process_team_members()
        self.identification_enabled = self.config.get("team_identification", {}).get("enabled", False)
        
    def load_config(self) -> Dict:
        """Загружает конфигурацию команды"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print(f"⚠️ Файл конфигурации команды {self.config_file} не найден")
                return {}
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации команды: {e}")
            return {}
    
    def _process_team_members(self) -> Dict:
        """Обрабатывает список участников команды для быстрого поиска"""
        processed = {}
        
        if not self.config.get("team_members"):
            return processed
        
        for team_name, team_members in self.config["team_members"].items():
            for member_id, member_info in team_members.items():
                # ИСПРАВЛЕНИЕ: используем поле 'team' из конфигурации, а не добавляем team_name
                team_field = member_info.get("team", team_name)
                
                processed[member_id] = {
                    **member_info,
                    "team_name": team_field,  # Используем значение из конфигурации
                    "search_terms": self._generate_search_terms(member_info)
                }
        
        return processed
    
    def _generate_search_terms(self, member_info: Dict) -> List[str]:
        """Генерирует поисковые термины для участника"""
        terms = []
        
        # Полное имя
        full_name = member_info.get("full_name", "")
        if full_name:
            terms.extend([full_name.lower(), full_name])
            # Разбиваем на части
            name_parts = full_name.split()
            terms.extend([part.lower() for part in name_parts])
        
        # Псевдонимы
        aliases = member_info.get("aliases", [])
        terms.extend([alias.lower() for alias in aliases])
        
        # Голосовые ключевые слова
        voice_keywords = member_info.get("voice_keywords", [])
        terms.extend(voice_keywords)
        
        # Уникальные термины
        return list(set(terms))
    
    def should_apply_identification(self, template_type: str) -> bool:
        """Проверяет, нужно ли применять идентификацию для данного типа встречи"""
        if not self.identification_enabled:
            return False
        
        apply_to_templates = self.config.get("team_identification", {}).get("apply_to_templates", [])
        return template_type in apply_to_templates or len(apply_to_templates) == 0
    
    def get_team_statistics(self) -> Dict:
        """Возвращает статистику команды из конфигурации"""
        stats = {
            "total_members": 0,
            "teams": {},
            "team_breakdown": {}
        }
        
        team_members = self.config.get("team_members", {})
        
        for team_name, members in team_members.items():
            if isinstance(members, dict):
                member_count = len(members)
                stats["teams"][team_name] = member_count
                stats["team_breakdown"][team_name] = list(members.keys())
                stats["total_members"] += member_count
        
        return stats
    
    def identify_participants(self, transcript: str, template_type: str = "standard") -> Dict:
        """Определяет участников встречи в транскрипте"""
        if not self.should_apply_identification(template_type):
            return {"identified": False, "reason": "identification_disabled"}
        
        if not self.team_members:
            return {"identified": False, "reason": "no_team_config"}
        
        # Извлекаем спикеров из транскрипта
        speakers = self._extract_speakers_from_transcript(transcript)
        
        # Идентифицируем каждого спикера
        identified_speakers = {}
        confidence_scores = {}
        
        for speaker_id, speaker_text in speakers.items():
            best_match = self._find_best_match(speaker_text, template_type)
            
            if best_match:
                identified_speakers[speaker_id] = best_match["member_info"]
                confidence_scores[speaker_id] = best_match["confidence"]
        
        # Формируем результат
        result = {
            "identified": True,
            "template_type": template_type,
            "speakers": identified_speakers,
            "confidence_scores": confidence_scores,
            "statistics": self._generate_statistics(identified_speakers),
            "replacements": self._generate_replacements(identified_speakers),
            "participant_summary": self._generate_participant_summary(identified_speakers)
        }
        
        return result
    
    def _extract_speakers_from_transcript(self, transcript: str) -> Dict[str, str]:
        """Извлекает речь каждого спикера из транскрипта"""
        speakers = {}
        
        # Паттерны для поиска спикеров
        patterns = [
            r'Спикер (\d+):\s*(.+?)(?=\n\nСпикер \d+:|$)',
            r'Speaker (\d+):\s*(.+?)(?=\n\nSpeaker \d+:|$)',
            r'Участник (\d+):\s*(.+?)(?=\n\nУчастник \d+:|$)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, transcript, re.DOTALL | re.IGNORECASE)
            if matches:
                for speaker_id, text in matches:
                    speakers[f"Спикер {speaker_id}"] = text.strip()
                break
        
        # Если не найдены спикеры, анализируем весь текст
        if not speakers:
            speakers["Unknown"] = transcript
        
        return speakers
    
    def _find_best_match(self, speaker_text: str, template_type: str) -> Optional[Dict]:
        """Находит наилучшее совпадение для спикера"""
        best_match = None
        best_score = 0
        
        threshold = self.config.get("team_identification", {}).get("confidence_threshold", 0.7)
        
        for member_id, member_info in self.team_members.items():
            score = self._calculate_match_score(speaker_text, member_info, template_type)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = {
                    "member_id": member_id,
                    "member_info": member_info,
                    "confidence": score
                }
        
        return best_match
    
    def _calculate_match_score(self, speaker_text: str, member_info: Dict, template_type: str) -> float:
        """Вычисляет оценку совпадения для участника"""
        total_score = 0.0
        strategies = self.config.get("identification_rules", {}).get("matching_strategies", [])
        
        # Значения по умолчанию, если нет конфигурации
        if not strategies:
            strategies = [
                {"strategy": "exact_name_match", "weight": 1.0},
                {"strategy": "alias_match", "weight": 0.9},
                {"strategy": "voice_keyword_match", "weight": 0.8},
                {"strategy": "partial_name_match", "weight": 0.7},
                {"strategy": "role_context_match", "weight": 0.6}
            ]
        
        text_lower = speaker_text.lower()
        
        for strategy in strategies:
            strategy_name = strategy["strategy"]
            weight = strategy["weight"]
            score = 0.0
            
            if strategy_name == "exact_name_match":
                full_name = member_info.get("full_name", "").lower()
                if full_name in text_lower:
                    score = 1.0
            
            elif strategy_name == "alias_match":
                aliases = member_info.get("aliases", [])
                for alias in aliases:
                    if alias.lower() in text_lower:
                        score = max(score, 0.9)
            
            elif strategy_name == "voice_keyword_match":
                keywords = member_info.get("voice_keywords", [])
                for keyword in keywords:
                    if keyword in text_lower:
                        score = max(score, 0.8)
            
            elif strategy_name == "partial_name_match":
                search_terms = member_info.get("search_terms", [])
                for term in search_terms:
                    if len(term) > 2:  # Избегаем слишком коротких совпадений
                        if fuzz:
                            fuzzy_score = fuzz.partial_ratio(term, text_lower) / 100.0
                            if fuzzy_score > 0.8:
                                score = max(score, fuzzy_score * 0.7)
                        else:
                            # Упрощенное сравнение без fuzzywuzzy
                            if term in text_lower:
                                score = max(score, 0.7)
            
            elif strategy_name == "role_context_match":
                score = self._check_role_context(text_lower, member_info, template_type)
            
            total_score += score * weight
        
        # Нормализуем оценку
        max_possible_score = sum(s["weight"] for s in strategies)
        if max_possible_score > 0:
            total_score = total_score / max_possible_score
        
        return min(total_score, 1.0)
    
    def _check_role_context(self, text: str, member_info: Dict, template_type: str) -> float:
        """Проверяет контекст роли участника"""
        team_name = member_info.get("team_name", "")
        context_keywords = self.config.get("identification_rules", {}).get("context_keywords", {})
        
        if template_type not in context_keywords:
            return 0.0
        
        team_keywords = context_keywords[template_type].get(team_name, [])
        
        matches = 0
        for keyword in team_keywords:
            if keyword.lower() in text:
                matches += 1
        
        if len(team_keywords) > 0:
            return matches / len(team_keywords)
        
        return 0.0
    
    def _generate_statistics(self, identified_speakers: Dict) -> Dict:
        """Генерирует статистику по участникам"""
        stats = {
            "total_identified": len(identified_speakers),
            "teams_present": set(),
            "roles_present": set(),
            "team_breakdown": defaultdict(int)
        }
        
        for speaker_info in identified_speakers.values():
            team = speaker_info.get("team_name", "unknown")
            role = speaker_info.get("role", "unknown")
            
            stats["teams_present"].add(team)
            stats["roles_present"].add(role)
            stats["team_breakdown"][team] += 1
        
        stats["teams_present"] = list(stats["teams_present"])
        stats["roles_present"] = list(stats["roles_present"])
        stats["team_breakdown"] = dict(stats["team_breakdown"])
        
        return stats
    
    def _generate_replacements(self, identified_speakers: Dict) -> Dict[str, str]:
        """Генерирует замены спикеров для транскрипта"""
        replacements = {}
        
        for speaker_id, member_info in identified_speakers.items():
            full_name = member_info.get("full_name", "")
            role = member_info.get("role", "")
            
            if self.config.get("output_formatting", {}).get("include_roles", False):
                replacement = f"{full_name} ({role})"
            else:
                replacement = full_name
            
            replacements[speaker_id] = replacement
        
        return replacements
    
    def _generate_participant_summary(self, identified_speakers: Dict) -> str:
        """Генерирует краткое описание участников"""
        if not identified_speakers:
            return "Участники не определены"
        
        summary_parts = []
        
        # Группируем по командам
        if self.config.get("output_formatting", {}).get("group_by_teams", True):
            teams = defaultdict(list)
            
            for member_info in identified_speakers.values():
                team_name = member_info.get("team_name", "unknown")
                teams[team_name].append(member_info)
            
            team_names_ru = {
                "management": "Руководство",
                "development": "Разработка", 
                "testing": "Тестирование",
                "analytics": "Аналитика"
            }
            
            for team_name, members in teams.items():
                team_display = team_names_ru.get(team_name, team_name.title())
                summary_parts.append(f"\n**{team_display}:**")
                
                for member in members:
                    name = member.get("full_name", "")
                    role = member.get("role", "")
                    
                    if self.config.get("output_formatting", {}).get("highlight_team_leads", True) and "lead" in role.lower():
                        summary_parts.append(f"• **{name}** - {role}")
                    else:
                        summary_parts.append(f"• {name} - {role}")
        
        else:
            # Простой список
            for member_info in identified_speakers.values():
                name = member_info.get("full_name", "")
                role = member_info.get("role", "")
                summary_parts.append(f"• {name} - {role}")
        
        return "\n".join(summary_parts)
    
    def apply_speaker_replacements(self, transcript: str, template_type: str = "standard") -> str:
        """Применяет замены спикеров в транскрипте"""
        identification_result = self.identify_participants(transcript, template_type)
        
        if not identification_result.get("identified", False):
            return transcript
        
        replacements = identification_result.get("replacements", {})
        modified_transcript = transcript
        
        # Применяем замены
        for old_speaker, new_speaker in replacements.items():
            # Заменяем различные форматы спикеров
            patterns = [
                rf'\b{re.escape(old_speaker)}\b',
                rf'Спикер {re.escape(old_speaker.split()[-1])}\b',
                rf'Speaker {re.escape(old_speaker.split()[-1])}\b'
            ]
            
            for pattern in patterns:
                modified_transcript = re.sub(
                    pattern, 
                    new_speaker, 
                    modified_transcript, 
                    flags=re.IGNORECASE
                )
        
        return modified_transcript
    
    def get_team_context_for_template(self, template_type: str, identified_speakers: Dict) -> str:
        """Получает контекст команды для шаблона"""
        if not identified_speakers:
            return ""
        
        context_parts = []
        
        # Добавляем информацию о составе встречи
        stats = self._generate_statistics(identified_speakers)
        
        context_parts.append("**Состав встречи:**")
        context_parts.append(self._generate_participant_summary(identified_speakers))
        
        # Добавляем статистику команд
        if len(stats["teams_present"]) > 1:
            context_parts.append(f"\n**Представлены команды:** {', '.join(stats['teams_present'])}")
        
        # Специфичный контекст для стендапов
        if template_type == "standup":
            context_parts.append("\n**Формат стендапа:** что делал вчера, планы на сегодня, блокеры")
        
        return "\n".join(context_parts)

def main():
    """Функция для тестирования модуля"""
    print("🔍 ТЕСТИРОВАНИЕ ИДЕНТИФИКАЦИИ УЧАСТНИКОВ КОМАНДЫ")
    print("=" * 60)
    
    identifier = TeamIdentifier()
    
    if not identifier.identification_enabled:
        print("❌ Идентификация участников отключена в конфигурации")
        print("💡 Проверьте настройку 'enabled' в team_config.json")
        return
    
    # Показываем статистику команды
    team_stats = identifier.get_team_statistics()
    print(f"📊 СТАТИСТИКА КОМАНДЫ:")
    print(f"Общее количество участников: {team_stats['total_members']}")
    print(f"Команд: {len(team_stats['teams'])}")
    
    for team_name, count in team_stats["teams"].items():
        team_display = {
            "management": "Руководство",
            "development": "Разработка",
            "testing": "Тестирование", 
            "analytics": "Аналитика"
        }.get(team_name, team_name)
        print(f"  {team_display}: {count} чел.")
    
    # Тестовый транскрипт
    test_transcript = """
Спикер 0: Доброе утро всем! Начинаем стендап. Влад, как дела с новой фичей?

Спикер 1: Привет! Вчера закончил работу над авторизацией, сегодня планирую заняться интеграцией с API. Блокеров нет.

Спикер 2: Отлично, Владислав. А как у нас дела с тестированием? Юля, что скажешь?

Спикер 3: Вчера протестировала новый модуль, нашла несколько багов. Саша поможет с автотестами сегодня.

Спикер 4: Да, помогу Юле с автотестами. У меня вчера была работа с регрессионным тестированием.
"""
    
    print(f"\n📝 Тестовый транскрипт:")
    print(test_transcript[:200] + "...")
    
    # Тестируем идентификацию
    result = identifier.identify_participants(test_transcript, "standup")
    
    print(f"\n🎯 Результаты идентификации:")
    print(f"Статус: {'✅ Успешно' if result['identified'] else '❌ Не удалось'}")
    
    if result["identified"]:
        print(f"Участвующие команды: {', '.join(result['statistics']['teams_present'])}")
        print(f"Идентифицировано участников: {result['statistics']['total_identified']}")
        
        print(f"\n👥 Участники встречи:")
        print(result["participant_summary"])
        
        print(f"\n🔄 Замены в транскрипте:")
        for old, new in result["replacements"].items():
            confidence = result["confidence_scores"].get(old, 0)
            print(f"   {old} → {new} (уверенность: {confidence:.0%})")
        
        # Применяем замены
        modified_transcript = identifier.apply_speaker_replacements(test_transcript, "standup")
        print(f"\n📝 Модифицированный транскрипт (первые 300 символов):")
        print(modified_transcript[:300] + "...")
    else:
        print(f"Причина: {result.get('reason', 'неизвестно')}")

if __name__ == "__main__":
    main()
