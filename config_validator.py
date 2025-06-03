#!/usr/bin/env python3
"""
Валидатор конфигурации team_config.json
"""

import json
import os
from typing import Dict, List, Tuple, Any
from pathlib import Path

class ConfigValidator:
    """Класс для валидации конфигурации команды"""
    
    def __init__(self, config_file: str = "team_config.json"):
        self.config_file = config_file
        self.errors = []
        self.warnings = []
        
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Основная функция валидации"""
        self.errors = []
        self.warnings = []
        
        # Проверяем существование файла
        if not os.path.exists(self.config_file):
            self.errors.append(f"❌ Файл конфигурации {self.config_file} не найден")
            return False, self.errors, self.warnings
        
        # Загружаем конфигурацию
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"❌ Ошибка парсинга JSON: {e}")
            return False, self.errors, self.warnings
        except Exception as e:
            self.errors.append(f"❌ Ошибка чтения файла: {e}")
            return False, self.errors, self.warnings
        
        # Выполняем проверки
        self._validate_structure(config)
        self._validate_team_identification(config)
        self._validate_team_members(config)
        self._validate_identification_rules(config)
        self._validate_output_formatting(config)
        self._validate_consistency(config)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_structure(self, config: Dict):
        """Проверяет общую структуру конфигурации"""
        required_sections = ["team_identification", "team_members"]
        
        for section in required_sections:
            if section not in config:
                self.errors.append(f"❌ Отсутствует обязательная секция: {section}")
        
        # Проверяем типы данных
        if not isinstance(config, dict):
            self.errors.append("❌ Корневая структура должна быть объектом JSON")
    
    def _validate_team_identification(self, config: Dict):
        """Проверяет секцию team_identification"""
        if "team_identification" not in config:
            return
        
        team_id = config["team_identification"]
        
        # Проверяем обязательные поля
        if "enabled" not in team_id:
            self.errors.append("❌ team_identification.enabled не указан")
        elif not isinstance(team_id["enabled"], bool):
            self.errors.append("❌ team_identification.enabled должен быть boolean")
        
        # Проверяем apply_to_templates
        if "apply_to_templates" in team_id:
            templates = team_id["apply_to_templates"]
            if not isinstance(templates, list):
                self.errors.append("❌ apply_to_templates должен быть массивом")
            else:
                valid_templates = ["standup", "project", "review", "business", "standard"]
                for template in templates:
                    if template not in valid_templates:
                        self.warnings.append(f"⚠️ Неизвестный шаблон: {template}")
        
        # Проверяем порог уверенности
        if "confidence_threshold" in team_id:
            threshold = team_id["confidence_threshold"]
            if not isinstance(threshold, (int, float)):
                self.errors.append("❌ confidence_threshold должен быть числом")
            elif not 0.0 <= threshold <= 1.0:
                self.errors.append("❌ confidence_threshold должен быть от 0.0 до 1.0")
        
        # Проверяем булевы флаги
        bool_fields = ["fuzzy_matching", "partial_name_matching"]
        for field in bool_fields:
            if field in team_id and not isinstance(team_id[field], bool):
                self.errors.append(f"❌ {field} должен быть boolean")
    
    def _validate_team_members(self, config: Dict):
        """Проверяет секцию team_members"""
        if "team_members" not in config:
            self.errors.append("❌ Отсутствует секция team_members")
            return
        
        teams = config["team_members"]
        
        if not isinstance(teams, dict):
            self.errors.append("❌ team_members должен быть объектом")
            return
        
        if len(teams) == 0:
            self.warnings.append("⚠️ team_members пуст - никто не будет идентифицирован")
        
        # Проверяем каждую команду
        for team_name, team_members in teams.items():
            self._validate_team(team_name, team_members)
    
    def _validate_team(self, team_name: str, team_members: Dict):
        """Проверяет конкретную команду"""
        if not isinstance(team_members, dict):
            self.errors.append(f"❌ Команда {team_name} должна быть объектом")
            return
        
        if len(team_members) == 0:
            self.warnings.append(f"⚠️ Команда {team_name} пуста")
        
        # Проверяем каждого участника
        for member_id, member_info in team_members.items():
            self._validate_member(team_name, member_id, member_info)
    
    def _validate_member(self, team_name: str, member_id: str, member_info: Dict):
        """Проверяет конкретного участника"""
        if not isinstance(member_info, dict):
            self.errors.append(f"❌ Участник {team_name}.{member_id} должен быть объектом")
            return
        
        # Обязательные поля
        required_fields = ["full_name", "role"]
        for field in required_fields:
            if field not in member_info:
                self.errors.append(f"❌ Участник {team_name}.{member_id}: отсутствует {field}")
            elif not isinstance(member_info[field], str) or not member_info[field].strip():
                self.errors.append(f"❌ Участник {team_name}.{member_id}: {field} должен быть непустой строкой")
        
        # Проверяем team - должен совпадать с team_name
        if "team" in member_info:
            if member_info["team"] != team_name:
                self.errors.append(f"❌ Участник {team_name}.{member_id}: поле team ({member_info['team']}) не совпадает с командой ({team_name})")
        
        # Проверяем массивы
        array_fields = ["aliases", "voice_keywords"]
        for field in array_fields:
            if field in member_info:
                if not isinstance(member_info[field], list):
                    self.errors.append(f"❌ Участник {team_name}.{member_id}: {field} должен быть массивом")
                else:
                    # Проверяем элементы массива
                    for item in member_info[field]:
                        if not isinstance(item, str):
                            self.errors.append(f"❌ Участник {team_name}.{member_id}: элементы {field} должны быть строками")
        
        # Проверяем наличие поисковых терминов
        if not member_info.get("aliases") and not member_info.get("voice_keywords"):
            self.warnings.append(f"⚠️ Участник {team_name}.{member_id}: нет aliases или voice_keywords - идентификация может быть затруднена")
    
    def _validate_identification_rules(self, config: Dict):
        """Проверяет секцию identification_rules"""
        if "identification_rules" not in config:
            self.warnings.append("⚠️ Отсутствует секция identification_rules - будут использованы значения по умолчанию")
            return
        
        rules = config["identification_rules"]
        
        # Проверяем speaker_mapping
        if "speaker_mapping" in rules:
            mapping = rules["speaker_mapping"]
            bool_fields = ["enabled", "auto_replace_speakers", "create_participant_summary"]
            for field in bool_fields:
                if field in mapping and not isinstance(mapping[field], bool):
                    self.errors.append(f"❌ identification_rules.speaker_mapping.{field} должен быть boolean")
        
        # Проверяем matching_strategies
        if "matching_strategies" in rules:
            strategies = rules["matching_strategies"]
            if not isinstance(strategies, list):
                self.errors.append("❌ matching_strategies должен быть массивом")
            else:
                self._validate_strategies(strategies)
        
        # Проверяем context_keywords
        if "context_keywords" in rules:
            keywords = rules["context_keywords"]
            if not isinstance(keywords, dict):
                self.errors.append("❌ context_keywords должен быть объектом")
    
    def _validate_strategies(self, strategies: List):
        """Проверяет стратегии сопоставления"""
        required_strategy_fields = ["strategy", "weight"]
        valid_strategies = [
            "exact_name_match", "alias_match", "voice_keyword_match", 
            "partial_name_match", "role_context_match"
        ]
        
        for i, strategy in enumerate(strategies):
            if not isinstance(strategy, dict):
                self.errors.append(f"❌ Стратегия {i}: должна быть объектом")
                continue
            
            # Проверяем обязательные поля
            for field in required_strategy_fields:
                if field not in strategy:
                    self.errors.append(f"❌ Стратегия {i}: отсутствует поле {field}")
            
            # Проверяем название стратегии
            if "strategy" in strategy:
                if strategy["strategy"] not in valid_strategies:
                    self.errors.append(f"❌ Стратегия {i}: неизвестная стратегия {strategy['strategy']}")
            
            # Проверяем вес
            if "weight" in strategy:
                weight = strategy["weight"]
                if not isinstance(weight, (int, float)):
                    self.errors.append(f"❌ Стратегия {i}: weight должен быть числом")
                elif weight < 0:
                    self.errors.append(f"❌ Стратегия {i}: weight не может быть отрицательным")
    
    def _validate_output_formatting(self, config: Dict):
        """Проверяет секцию output_formatting"""
        if "output_formatting" not in config:
            return
        
        formatting = config["output_formatting"]
        bool_fields = [
            "use_full_names", "include_roles", "group_by_teams", 
            "add_team_structure", "highlight_team_leads"
        ]
        
        for field in bool_fields:
            if field in formatting and not isinstance(formatting[field], bool):
                self.errors.append(f"❌ output_formatting.{field} должен быть boolean")
    
    def _validate_consistency(self, config: Dict):
        """Проверяет консистентность данных"""
        # Собираем статистику
        if "team_members" not in config:
            return
        
        teams = config["team_members"]
        total_members = 0
        team_stats = {}
        
        for team_name, members in teams.items():
            if isinstance(members, dict):
                team_stats[team_name] = len(members)
                total_members += len(members)
        
        # Проверяем разумность количества участников
        if total_members == 0:
            self.errors.append("❌ В конфигурации нет ни одного участника")
        elif total_members > 100:
            self.warnings.append(f"⚠️ Очень много участников ({total_members}) - возможны проблемы с производительностью")
        
        # Проверяем сбалансированность команд
        if len(team_stats) > 1:
            max_team_size = max(team_stats.values())
            min_team_size = min(team_stats.values())
            
            if max_team_size > min_team_size * 10:
                self.warnings.append("⚠️ Очень несбалансированные размеры команд")
        
        # Проверяем дублирование имен
        self._check_duplicate_names(teams)
    
    def _check_duplicate_names(self, teams: Dict):
        """Проверяет дублирование имен участников"""
        all_names = []
        all_aliases = []
        
        for team_name, members in teams.items():
            if not isinstance(members, dict):
                continue
                
            for member_id, member_info in members.items():
                if not isinstance(member_info, dict):
                    continue
                
                # Собираем имена
                full_name = member_info.get("full_name", "")
                if full_name:
                    all_names.append((full_name, f"{team_name}.{member_id}"))
                
                # Собираем псевдонимы
                aliases = member_info.get("aliases", [])
                for alias in aliases:
                    all_aliases.append((alias, f"{team_name}.{member_id}"))
        
        # Проверяем дублирование полных имен
        name_counts = {}
        for name, member_path in all_names:
            if name in name_counts:
                name_counts[name].append(member_path)
            else:
                name_counts[name] = [member_path]
        
        for name, paths in name_counts.items():
            if len(paths) > 1:
                self.errors.append(f"❌ Дублирование имени '{name}' у участников: {', '.join(paths)}")
        
        # Проверяем дублирование псевдонимов
        alias_counts = {}
        for alias, member_path in all_aliases:
            if alias in alias_counts:
                alias_counts[alias].append(member_path)
            else:
                alias_counts[alias] = [member_path]
        
        for alias, paths in alias_counts.items():
            if len(paths) > 1:
                self.warnings.append(f"⚠️ Дублирование псевдонима '{alias}' у участников: {', '.join(paths)}")

def run_validation_tests():
    """Запускает полную валидацию конфигурации"""
    print("🔍 ВАЛИДАЦИЯ КОНФИГУРАЦИИ TEAM_CONFIG.JSON")
    print("=" * 60)
    
    validator = ConfigValidator()
    is_valid, errors, warnings = validator.validate()
    
    # Выводим результаты
    if is_valid:
        print("✅ КОНФИГУРАЦИЯ ВАЛИДНА")
    else:
        print("❌ КОНФИГУРАЦИЯ СОДЕРЖИТ ОШИБКИ")
    
    if errors:
        print(f"\n🚨 ОШИБКИ ({len(errors)}):")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print(f"\n⚠️ ПРЕДУПРЕЖДЕНИЯ ({len(warnings)}):")
        for warning in warnings:
            print(f"  {warning}")
    
    if not errors and not warnings:
        print("\n🎉 Конфигурация идеальна!")
    
    # Дополнительные проверки
    print(f"\n📊 СТАТИСТИКА:")
    if os.path.exists("team_config.json"):
        try:
            with open("team_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            
            teams = config.get("team_members", {})
            total_members = sum(len(members) for members in teams.values() if isinstance(members, dict))
            print(f"  Команд: {len(teams)}")
            print(f"  Участников: {total_members}")
            
            # Разбивка по командам
            for team_name, members in teams.items():
                if isinstance(members, dict):
                    print(f"    {team_name}: {len(members)} чел.")
            
        except Exception as e:
            print(f"  Ошибка чтения статистики: {e}")
    
    return is_valid

def main():
    """Основная функция"""
    success = run_validation_tests()
    
    if not success:
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        print("1. Исправьте все ошибки в team_config.json")
        print("2. Обратите внимание на предупреждения")
        print("3. Запустите валидацию повторно")
        print("4. Протестируйте с помощью: python team_identification_demo.py")
        
        sys.exit(1)
    else:
        print(f"\n🎉 КОНФИГУРАЦИЯ ГОТОВА К ИСПОЛЬЗОВАНИЮ!")
        print("Можно запускать: python team_identification_demo.py")

if __name__ == "__main__":
    import sys
    main()
