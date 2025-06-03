#!/usr/bin/env python3
"""
Модуль для интеллектуальной замены спикеров в транскриптах
Объединяет результаты анализа протокола и team_identifier для создания точных замен
"""

import re
from typing import Dict, List, Optional, Tuple

class SpeakerMapper:
    """Класс для интеллектуального сопоставления и замены спикеров"""
    
    def __init__(self, team_identifier=None):
        """
        Инициализация mapper'а спикеров
        
        Args:
            team_identifier: Экземпляр TeamIdentifier для доступа к базе команды
        """
        self.team_identifier = team_identifier
    
    def create_combined_speaker_mapping(self, transcript: str, protocol: str, 
                                      protocol_id: Dict, transcript_id: Dict) -> Dict[str, str]:
        """
        Создает комбинированную карту замен спикеров
        
        Args:
            transcript: Исходный транскрипт
            protocol: Сгенерированный протокол
            protocol_id: Результат идентификации по протоколу
            transcript_id: Результат идентификации по транскрипту
            
        Returns:
            Dict: Карта замен {старое_имя: новое_имя}
        """
        replacements = {}
        
        # Извлекаем информацию из протокола о спикерах с именами
        name_pattern = r'Спикер (\d+) \(([^)]+)\):'
        named_speakers = re.findall(name_pattern, protocol)
        
        # Создаем карту: номер спикера -> имя из протокола
        protocol_names = {}
        for speaker_num, name in named_speakers:
            clean_name = name.strip()
            protocol_names[f"Спикер {speaker_num}"] = clean_name
        
        # Проверяем идентификации из team_identifier
        identified_speakers = {}
        
        if transcript_id and transcript_id.get("identified"):
            for speaker_id, member_info in transcript_id.get("speakers", {}).items():
                full_name = member_info.get("full_name", "")
                if full_name:
                    identified_speakers[speaker_id] = full_name
        
        if protocol_id and protocol_id.get("identified"):
            for speaker_id, member_info in protocol_id.get("speakers", {}).items():
                full_name = member_info.get("full_name", "")
                if full_name and speaker_id not in identified_speakers:
                    identified_speakers[speaker_id] = full_name
        
        # Приоритет замен:
        # 1. Точные идентификации из team_identifier
        # 2. Имена из протокола с сопоставлением в базе команды
        
        for speaker_key in protocol_names.keys():
            if speaker_key in identified_speakers:
                # Приоритет у точной идентификации
                replacements[speaker_key] = identified_speakers[speaker_key]
            else:
                # Используем имя из протокола
                protocol_name = protocol_names[speaker_key]
                
                # Попытаемся найти это имя в базе команды
                matched_member = self.find_team_member_by_name(protocol_name)
                if matched_member:
                    replacements[speaker_key] = matched_member["full_name"]
                else:
                    # Используем имя как есть
                    replacements[speaker_key] = protocol_name
        
        # Добавляем остальные идентификации
        for speaker_key, full_name in identified_speakers.items():
            if speaker_key not in replacements:
                replacements[speaker_key] = full_name
        
        return replacements
    
    def find_team_member_by_name(self, name: str) -> Optional[Dict]:
        """
        Ищет участника команды по имени
        
        Args:
            name: Имя для поиска
            
        Returns:
            Dict или None: Информация о найденном участнике команды
        """
        if not self.team_identifier:
            return None
        
        name_lower = name.lower()
        
        for member_id, member_info in self.team_identifier.team_members.items():
            # Проверяем полное имя
            full_name = member_info.get("full_name", "").lower()
            if name_lower in full_name or full_name in name_lower:
                return member_info
            
            # Проверяем псевдонимы
            for alias in member_info.get("aliases", []):
                if name_lower in alias.lower() or alias.lower() in name_lower:
                    return member_info
            
            # Проверяем ключевые слова
            for keyword in member_info.get("voice_keywords", []):
                if name_lower in keyword.lower() or keyword.lower() in name_lower:
                    return member_info
        
        return None
    
    def apply_speaker_replacements_to_transcript(self, transcript: str, replacements: Dict[str, str]) -> str:
        """
        Применяет замены спикеров к транскрипту
        
        Args:
            transcript: Исходный транскрипт
            replacements: Карта замен
            
        Returns:
            str: Модифицированный транскрипт
        """
        modified_transcript = transcript
        
        for old_speaker, new_name in replacements.items():
            # Заменяем в заголовках спикеров
            pattern = rf'\b{re.escape(old_speaker)}:'
            replacement = f'{new_name}:'
            modified_transcript = re.sub(pattern, replacement, modified_transcript)
            
            # Заменяем упоминания в тексте
            pattern = rf'\b{re.escape(old_speaker)}\b'
            modified_transcript = re.sub(pattern, new_name, modified_transcript)
        
        return modified_transcript
    
    def create_final_team_identification(self, replacements: Dict[str, str], 
                                       protocol_id: Dict, transcript_id: Dict) -> Dict:
        """
        Создает финальный объект team_identification
        
        Args:
            replacements: Карта замен спикеров
            protocol_id: Результат идентификации по протоколу
            transcript_id: Результат идентификации по транскрипту
            
        Returns:
            Dict: Финальный объект team_identification
        """
        
        # Базовая структура
        result = {
            "identified": len(replacements) > 0,
            "template_type": protocol_id.get("template_type") or transcript_id.get("template_type", "unknown"),
            "speakers": {},
            "confidence_scores": {},
            "statistics": {
                "total_identified": len(replacements),
                "teams_present": [],
                "roles_present": [],
                "team_breakdown": {}
            },
            "replacements": replacements,
            "participant_summary": ""
        }
        
        if not self.team_identifier:
            return result
        
        # Заполняем информацию о спикерах
        teams_present = set()
        roles_present = set()
        team_breakdown = {}
        
        for speaker_key, name in replacements.items():
            # Ищем информацию о члене команды
            member_info = None
            for member_id, info in self.team_identifier.team_members.items():
                if info.get("full_name") == name:
                    member_info = info.copy()
                    member_info["member_id"] = member_id
                    break
            
            if member_info:
                team = member_info.get("team", "unknown")
                role = member_info.get("role", "unknown")
                
                teams_present.add(team)
                roles_present.add(role)
                
                if team not in team_breakdown:
                    team_breakdown[team] = 0
                team_breakdown[team] += 1
                
                result["speakers"][speaker_key] = member_info
                result["confidence_scores"][speaker_key] = 0.95
            else:
                # Создаем базовую информацию для неизвестного участника
                result["speakers"][speaker_key] = {
                    "full_name": name,
                    "role": "unknown",
                    "team": "unknown",
                    "member_id": "unknown"
                }
                result["confidence_scores"][speaker_key] = 0.7
        
        result["statistics"]["teams_present"] = list(teams_present)
        result["statistics"]["roles_present"] = list(roles_present)
        result["statistics"]["team_breakdown"] = team_breakdown
        
        # Создаем краткое описание участников
        if replacements:
            summary_parts = []
            for speaker, name in replacements.items():
                summary_parts.append(f"{speaker} → {name}")
            result["participant_summary"] = "; ".join(summary_parts)
        else:
            result["participant_summary"] = "Участники не определены"
        
        return result
    
    def replace_speaker_names_legacy(self, transcript: str, name_mapping: Dict[str, str]) -> str:
        """
        Устаревший метод замены имен спикеров согласно маппингу
        Оставлен для совместимости
        
        Args:
            transcript: Исходный транскрипт
            name_mapping: Карта замен имен
            
        Returns:
            str: Модифицированный транскрипт
        """
        if not name_mapping:
            return transcript
        
        modified_transcript = transcript
        for old_name, new_name in name_mapping.items():
            pattern = rf'\b{re.escape(old_name)}\b'
            modified_transcript = re.sub(pattern, new_name, modified_transcript, flags=re.IGNORECASE)
        
        return modified_transcript
    
    def extract_speaker_names_from_protocol(self, protocol: str) -> Dict[str, str]:
        """
        Извлекает имена спикеров из протокола
        
        Args:
            protocol: Текст протокола
            
        Returns:
            Dict: Карта {спикер: имя}
        """
        speaker_names = {}
        
        # Ищем паттерны типа "Спикер X (Имя):"
        name_pattern = r'Спикер (\d+) \(([^)]+)\):'
        matches = re.findall(name_pattern, protocol)
        
        for speaker_num, name in matches:
            speaker_key = f"Спикер {speaker_num}"
            clean_name = name.strip()
            speaker_names[speaker_key] = clean_name
        
        return speaker_names
    
    def extract_speakers_from_transcript(self, transcript: str) -> Dict[str, str]:
        """
        Извлекает всех спикеров из транскрипта
        
        Args:
            transcript: Исходный транскрипт
            
        Returns:
            Dict: Карта {спикер: первая_реплика}
        """
        speakers = {}
        
        # Ищем всех спикеров в транскрипте
        speaker_pattern = r'(Спикер \d+):\s*(.+?)(?=\n\n|\Z)'
        matches = re.findall(speaker_pattern, transcript, re.DOTALL)
        
        for speaker_id, text in matches:
            if speaker_id not in speakers:
                # Берем только первые 100 символов для анализа
                speakers[speaker_id] = text[:100].strip()
        
        return speakers
    
    def get_mapping_statistics(self, replacements: Dict[str, str]) -> Dict:
        """
        Получает статистику замен
        
        Args:
            replacements: Карта замен
            
        Returns:
            Dict: Статистика замен
        """
        stats = {
            "total_replacements": len(replacements),
            "team_members_found": 0,
            "external_speakers": 0,
            "teams_represented": set(),
            "roles_represented": set()
        }
        
        if not self.team_identifier:
            return stats
        
        for speaker, name in replacements.items():
            # Проверяем, есть ли этот человек в базе команды
            member_found = False
            for member_id, member_info in self.team_identifier.team_members.items():
                if member_info.get("full_name") == name:
                    stats["team_members_found"] += 1
                    stats["teams_represented"].add(member_info.get("team", "unknown"))
                    stats["roles_represented"].add(member_info.get("role", "unknown"))
                    member_found = True
                    break
            
            if not member_found:
                stats["external_speakers"] += 1
        
        # Конвертируем set в list для JSON сериализации
        stats["teams_represented"] = list(stats["teams_represented"])
        stats["roles_represented"] = list(stats["roles_represented"])
        
        return stats
