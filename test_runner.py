#!/usr/bin/env python3
"""
Комплексный тестировщик системы идентификации участников команды
"""

import json
import os
import sys
from typing import Dict, List, Tuple, Any
import tempfile
import shutil

# Импортируем наши модули
try:
    from config_validator import ConfigValidator
except ImportError:
    print("❌ config_validator.py не найден!")
    sys.exit(1)

try:
    from team_identifier import TeamIdentifier
except ImportError:
    print("❌ team_identifier.py не найден!")
    sys.exit(1)

class SystemTester:
    """Комплексный тестировщик системы"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        
    def run_all_tests(self) -> bool:
        """Запускает все тесты"""
        print("🧪 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ ИДЕНТИФИКАЦИИ")
        print("=" * 70)
        
        self.setup_test_environment()
        
        try:
            # Тесты конфигурации
            self.test_config_validation()
            self.test_config_loading()
            self.test_invalid_configs()
            
            # Тесты идентификации
            self.test_team_identifier_initialization()
            self.test_participant_identification()
            self.test_speaker_replacements()
            self.test_edge_cases()
            
            # Тесты производительности
            self.test_performance()
            
            # Итоговый отчет
            self.print_test_summary()
            
        finally:
            self.cleanup_test_environment()
        
        return all(result["passed"] for result in self.test_results)
    
    def setup_test_environment(self):
        """Настройка тестового окружения"""
        self.temp_dir = tempfile.mkdtemp()
        print(f"📁 Тестовое окружение: {self.temp_dir}")
    
    def cleanup_test_environment(self):
        """Очистка тестового окружения"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Тестовое окружение очищено")
    
    def add_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Добавляет результат теста"""
        self.test_results.append({
            "name": test_name,
            "passed": passed,
            "details": details
        })
        
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
        if details and not passed:
            print(f"   {details}")
    
    def create_test_config(self, config_data: Dict, filename: str = "test_config.json") -> str:
        """Создает тестовую конфигурацию"""
        config_path = os.path.join(self.temp_dir, filename)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return config_path
    
    def test_config_validation(self):
        """Тестирует валидацию конфигурации"""
        print("\n🔍 ТЕСТЫ ВАЛИДАЦИИ КОНФИГУРАЦИИ")
        print("-" * 40)
        
        # Тест 1: Валидная конфигурация
        valid_config = {
            "team_identification": {
                "enabled": True,
                "apply_to_templates": ["standup", "project"],
                "confidence_threshold": 0.7,
                "fuzzy_matching": True,
                "partial_name_matching": True
            },
            "team_members": {
                "development": {
                    "john_doe": {
                        "full_name": "John Doe",
                        "role": "Developer",
                        "team": "development",
                        "aliases": ["John", "JD"],
                        "voice_keywords": ["john", "doe"]
                    }
                }
            },
            "identification_rules": {
                "matching_strategies": [
                    {"strategy": "exact_name_match", "weight": 1.0},
                    {"strategy": "alias_match", "weight": 0.9}
                ]
            }
        }
        
        config_path = self.create_test_config(valid_config)
        validator = ConfigValidator(config_path)
        is_valid, errors, warnings = validator.validate()
        
        self.add_test_result(
            "Валидация корректной конфигурации",
            is_valid and len(errors) == 0,
            f"Ошибки: {errors}" if errors else ""
        )
        
        # Тест 2: Невалидная конфигурация
        invalid_config = {
            "team_identification": {
                "enabled": "not_boolean",  # Ошибка: должно быть boolean
                "confidence_threshold": 1.5  # Ошибка: больше 1.0
            },
            "team_members": {
                "development": {
                    "john_doe": {
                        "role": "Developer"
                        # Отсутствует full_name
                    }
                }
            }
        }
        
        config_path = self.create_test_config(invalid_config, "invalid_config.json")
        validator = ConfigValidator(config_path)
        is_valid, errors, warnings = validator.validate()
        
        self.add_test_result(
            "Обнаружение ошибок в невалидной конфигурации",
            not is_valid and len(errors) > 0,
            f"Найдено ошибок: {len(errors)}"
        )
    
    def test_config_loading(self):
        """Тестирует загрузку конфигурации"""
        print("\n📁 ТЕСТЫ ЗАГРУЗКИ КОНФИГУРАЦИИ")
        print("-" * 40)
        
        # Тест 1: Загрузка существующего файла
        test_config = {
            "team_identification": {"enabled": True},
            "team_members": {"test_team": {}}
        }
        
        config_path = self.create_test_config(test_config)
        identifier = TeamIdentifier(config_path)
        
        self.add_test_result(
            "Загрузка существующего файла конфигурации",
            identifier.config.get("team_identification", {}).get("enabled") == True,
            "Конфигурация загружена корректно"
        )
        
        # Тест 2: Загрузка несуществующего файла
        non_existent_path = os.path.join(self.temp_dir, "non_existent.json")
        identifier = TeamIdentifier(non_existent_path)
        
        self.add_test_result(
            "Обработка несуществующего файла конфигурации",
            len(identifier.config) == 0,
            "Возвращена пустая конфигурация"
        )
        
        # Тест 3: Невалидный JSON
        invalid_json_path = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_json_path, "w") as f:
            f.write("{ invalid json }")
        
        identifier = TeamIdentifier(invalid_json_path)
        
        self.add_test_result(
            "Обработка невалидного JSON",
            len(identifier.config) == 0,
            "Ошибка парсинга обработана корректно"
        )
    
    def test_invalid_configs(self):
        """Тестирует различные невалидные конфигурации"""
        print("\n⚠️ ТЕСТЫ НЕВАЛИДНЫХ КОНФИГУРАЦИЙ")
        print("-" * 40)
        
        test_cases = [
            {
                "name": "Отсутствует team_identification",
                "config": {"team_members": {}},
                "should_have_errors": True
            },
            {
                "name": "Отсутствует team_members",
                "config": {"team_identification": {"enabled": True}},
                "should_have_errors": True
            },
            {
                "name": "Пустая конфигурация",
                "config": {},
                "should_have_errors": True
            },
            {
                "name": "Дублирование имен участников",
                "config": {
                    "team_identification": {"enabled": True},
                    "team_members": {
                        "team1": {
                            "user1": {"full_name": "John Doe", "role": "Dev", "team": "team1"}
                        },
                        "team2": {
                            "user2": {"full_name": "John Doe", "role": "QA", "team": "team2"}
                        }
                    }
                },
                "should_have_errors": True
            }
        ]
        
        for test_case in test_cases:
            config_path = self.create_test_config(test_case["config"], f"{test_case['name']}.json")
            validator = ConfigValidator(config_path)
            is_valid, errors, warnings = validator.validate()
            
            expected_result = not test_case["should_have_errors"]
            actual_result = is_valid
            
            self.add_test_result(
                f"Тест: {test_case['name']}",
                expected_result == actual_result,
                f"Ошибки: {len(errors)}, Предупреждения: {len(warnings)}"
            )
    
    def test_team_identifier_initialization(self):
        """Тестирует инициализацию TeamIdentifier"""
        print("\n🔧 ТЕСТЫ ИНИЦИАЛИЗАЦИИ TEAMIDENTIFIER")
        print("-" * 40)
        
        # Создаем тестовую конфигурацию
        test_config = {
            "team_identification": {
                "enabled": True,
                "apply_to_templates": ["standup"],
                "confidence_threshold": 0.8
            },
            "team_members": {
                "development": {
                    "dev1": {
                        "full_name": "Иван Иванов",
                        "role": "Senior Developer",
                        "team": "development",
                        "aliases": ["Иван", "Ваня"],
                        "voice_keywords": ["иван", "ваня"]
                    }
                },
                "testing": {
                    "qa1": {
                        "full_name": "Мария Петрова",
                        "role": "QA Engineer",
                        "team": "testing",
                        "aliases": ["Мария", "Маша"],
                        "voice_keywords": ["мария", "маша"]
                    }
                }
            }
        }
        
        config_path = self.create_test_config(test_config)
        identifier = TeamIdentifier(config_path)
        
        # Тест 1: Корректная инициализация
        self.add_test_result(
            "Инициализация с валидной конфигурацией",
            identifier.identification_enabled == True,
            "Идентификация включена"
        )
        
        # Тест 2: Обработка участников команды
        self.add_test_result(
            "Обработка участников команды",
            len(identifier.team_members) == 2,
            f"Обработано {len(identifier.team_members)} участников"
        )
        
        # Тест 3: Генерация поисковых терминов
        dev1_member = identifier.team_members.get("dev1", {})
        search_terms = dev1_member.get("search_terms", [])
        
        self.add_test_result(
            "Генерация поисковых терминов",
            len(search_terms) > 0 and "иван" in search_terms,
            f"Сгенерировано {len(search_terms)} терминов"
        )
        
        # Тест 4: Статистика команды
        stats = identifier.get_team_statistics()
        
        self.add_test_result(
            "Подсчет статистики команды",
            stats["total_members"] == 2 and len(stats["teams"]) == 2,
            f"Всего участников: {stats['total_members']}, команд: {len(stats['teams'])}"
        )
    
    def test_participant_identification(self):
        """Тестирует идентификацию участников"""
        print("\n🎯 ТЕСТЫ ИДЕНТИФИКАЦИИ УЧАСТНИКОВ")
        print("-" * 40)
        
        # Создаем конфигурацию для тестов
        test_config = {
            "team_identification": {
                "enabled": True,
                "apply_to_templates": ["standup", "test"],
                "confidence_threshold": 0.6
            },
            "team_members": {
                "development": {
                    "vlad": {
                        "full_name": "Владислав Ульянов",
                        "role": "Team Lead",
                        "team": "development",
                        "aliases": ["Владислав", "Влад", "Ульянов"],
                        "voice_keywords": ["владислав", "влад", "ульянов"]
                    }
                },
                "testing": {
                    "yulia": {
                        "full_name": "Юлия Деньченко",
                        "role": "QA Lead",
                        "team": "testing",
                        "aliases": ["Юлия", "Юля", "Деньченко"],
                        "voice_keywords": ["юлия", "юля", "деньченко"]
                    }
                }
            }
        }
        
        config_path = self.create_test_config(test_config)
        identifier = TeamIdentifier(config_path)
        
        # Тест 1: Идентификация по полному имени
        transcript1 = "Спикер 0: Владислав, как дела с задачей?"
        result1 = identifier.identify_participants(transcript1, "test")
        
        self.add_test_result(
            "Идентификация по полному имени",
            result1.get("identified", False) and len(result1.get("speakers", {})) > 0,
            f"Идентифицировано спикеров: {len(result1.get('speakers', {}))}"
        )
        
        # Тест 2: Идентификация по псевдониму
        transcript2 = "Спикер 1: Влад работает над новой фичей"
        result2 = identifier.identify_participants(transcript2, "test")
        
        identified = result2.get("identified", False)
        speaker_info = list(result2.get("speakers", {}).values())
        correct_identification = (identified and len(speaker_info) > 0 and 
                                speaker_info[0].get("full_name") == "Владислав Ульянов")
        
        self.add_test_result(
            "Идентификация по псевдониму",
            correct_identification,
            f"Спикер идентифицирован как: {speaker_info[0].get('full_name', 'неизвестно') if speaker_info else 'никто'}"
        )
        
        # Тест 3: Множественная идентификация
        transcript3 = """
Спикер 0: Влад, как дела с задачей?
Спикер 1: Хорошо, почти закончил. Юля, готовы тесты?
Спикер 2: Да, Владислав, тесты готовы.
"""
        result3 = identifier.identify_participants(transcript3, "test")
        
        self.add_test_result(
            "Множественная идентификация",
            len(result3.get("speakers", {})) >= 2,
            f"Идентифицировано спикеров: {len(result3.get('speakers', {}))}"
        )
        
        # Тест 4: Применение к шаблонам
        should_apply_standup = identifier.should_apply_identification("standup")
        should_not_apply_business = identifier.should_apply_identification("business")
        
        self.add_test_result(
            "Применение к корректным шаблонам",
            should_apply_standup and not should_not_apply_business,
            f"standup: {should_apply_standup}, business: {should_not_apply_business}"
        )
    
    def test_speaker_replacements(self):
        """Тестирует замену спикеров в транскрипте"""
        print("\n🔄 ТЕСТЫ ЗАМЕНЫ СПИКЕРОВ")
        print("-" * 40)
        
        # Используем предыдущую конфигурацию
        test_config = {
            "team_identification": {"enabled": True, "confidence_threshold": 0.5},
            "team_members": {
                "development": {
                    "vlad": {
                        "full_name": "Владислав Ульянов",
                        "role": "Developer",
                        "team": "development",
                        "aliases": ["Влад"],
                        "voice_keywords": ["влад"]
                    }
                }
            },
            "output_formatting": {"include_roles": False}
        }
        
        config_path = self.create_test_config(test_config)
        identifier = TeamIdentifier(config_path)
        
        original_transcript = "Спикер 0: Влад, как дела?"
        modified_transcript = identifier.apply_speaker_replacements(original_transcript, "standup")
        
        self.add_test_result(
            "Замена спикеров в транскрипте",
            "Владислав Ульянов" in modified_transcript,
            f"Результат: {modified_transcript[:50]}..."
        )
    
    def test_edge_cases(self):
        """Тестирует пограничные случаи"""
        print("\n🌪️ ТЕСТЫ ПОГРАНИЧНЫХ СЛУЧАЕВ")
        print("-" * 40)
        
        # Тест 1: Пустой транскрипт
        empty_config = {
            "team_identification": {"enabled": True},
            "team_members": {"test": {"user": {"full_name": "Test User", "role": "Tester", "team": "test"}}}
        }
        
        config_path = self.create_test_config(empty_config)
        identifier = TeamIdentifier(config_path)
        
        result = identifier.identify_participants("", "standup")
        
        self.add_test_result(
            "Обработка пустого транскрипта",
            result.get("identified", False) == False or len(result.get("speakers", {})) == 0,
            "Пустой транскрипт обработан корректно"
        )
        
        # Тест 2: Очень длинный транскрипт
        long_transcript = "Спикер 0: " + "Очень длинный текст. " * 1000
        result = identifier.identify_participants(long_transcript, "standup")
        
        self.add_test_result(
            "Обработка очень длинного транскрипта",
            True,  # Просто проверяем, что не падает
            "Длинный транскрипт обработан без ошибок"
        )
        
        # Тест 3: Отключенная идентификация
        disabled_config = {
            "team_identification": {"enabled": False},
            "team_members": {"test": {"user": {"full_name": "Test User", "role": "Tester", "team": "test"}}}
        }
        
        config_path = self.create_test_config(disabled_config, "disabled_config.json")
        identifier = TeamIdentifier(config_path)
        
        result = identifier.identify_participants("Спикер 0: Тест", "standup")
        
        self.add_test_result(
            "Обработка при отключенной идентификации",
            result.get("identified", True) == False and result.get("reason") == "identification_disabled",
            f"Причина: {result.get('reason', 'неизвестно')}"
        )
        
        # Тест 4: Низкий порог уверенности
        low_threshold_config = {
            "team_identification": {"enabled": True, "confidence_threshold": 0.95},
            "team_members": {
                "test": {
                    "user": {
                        "full_name": "Редкое Имя",
                        "role": "Tester",
                        "team": "test",
                        "aliases": ["Редкое"],
                        "voice_keywords": ["редкое"]
                    }
                }
            }
        }
        
        config_path = self.create_test_config(low_threshold_config, "low_threshold.json")
        identifier = TeamIdentifier(config_path)
        
        result = identifier.identify_participants("Спикер 0: Похожее имя", "standup")
        
        self.add_test_result(
            "Обработка с высоким порогом уверенности",
            len(result.get("speakers", {})) == 0,  # Не должно найти совпадений
            f"Найдено совпадений: {len(result.get('speakers', {}))}"
        )
    
    def test_performance(self):
        """Тестирует производительность системы"""
        print("\n⚡ ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("-" * 40)
        
        import time
        
        # Создаем большую конфигурацию
        large_config = {
            "team_identification": {"enabled": True, "confidence_threshold": 0.7},
            "team_members": {}
        }
        
        # Генерируем много участников
        for team_num in range(5):
            team_name = f"team_{team_num}"
            large_config["team_members"][team_name] = {}
            
            for user_num in range(20):
                user_id = f"user_{team_num}_{user_num}"
                large_config["team_members"][team_name][user_id] = {
                    "full_name": f"Пользователь {team_num} {user_num}",
                    "role": f"Role {user_num}",
                    "team": team_name,
                    "aliases": [f"Пользователь{user_num}", f"User{user_num}"],
                    "voice_keywords": [f"пользователь{user_num}", f"user{user_num}"]
                }
        
        config_path = self.create_test_config(large_config, "large_config.json")
        
        # Тест инициализации
        start_time = time.time()
        identifier = TeamIdentifier(config_path)
        init_time = time.time() - start_time
        
        self.add_test_result(
            "Производительность инициализации (100 участников)",
            init_time < 1.0,  # Должно быть быстрее 1 секунды
            f"Время инициализации: {init_time:.3f}с"
        )
        
        # Тест идентификации
        test_transcript = """
Спикер 0: Пользователь 1 5, как дела?
Спикер 1: User3 работает над задачей
Спикер 2: Нужно обсудить с пользователь2
"""
        
        start_time = time.time()
        result = identifier.identify_participants(test_transcript, "standup")
        identification_time = time.time() - start_time
        
        self.add_test_result(
            "Производительность идентификации",
            identification_time < 0.5,  # Должно быть быстрее 0.5 секунды
            f"Время идентификации: {identification_time:.3f}с, найдено: {len(result.get('speakers', {}))}"
        )
    
    def print_test_summary(self):
        """Печатает итоговый отчет по тестам"""
        print("\n" + "=" * 70)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ПО ТЕСТИРОВАНИЮ")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"Всего тестов: {total_tests}")
        print(f"✅ Прошло: {passed_tests}")
        print(f"❌ Провалено: {failed_tests}")
        print(f"📈 Успешность: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n🚨 ПРОВАЛИВШИЕСЯ ТЕСТЫ:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"❌ {result['name']}")
                    if result["details"]:
                        print(f"   {result['details']}")
        
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        if failed_tests == 0:
            print("🎉 Все тесты прошли успешно! Система готова к использованию.")
        else:
            print("🔧 Исправьте ошибки и запустите тесты повторно.")
            print("📝 Проверьте конфигурацию team_config.json")
            print("🐛 Убедитесь, что все зависимости установлены (fuzzywuzzy)")
        
        return failed_tests == 0

def create_sample_config():
    """Создает образец конфигурации для тестирования"""
    sample_config = {
        "team_identification": {
            "enabled": True,
            "apply_to_templates": ["standup", "project", "review"],
            "confidence_threshold": 0.7,
            "fuzzy_matching": True,
            "partial_name_matching": True
        },
        
        "team_members": {
            "management": {
                "egorov_oleg": {
                    "full_name": "Егоров Олег",
                    "role": "Руководитель проекта, product owner",
                    "team": "management",
                    "aliases": ["Олег", "Егоров", "PO", "продакт оунер"],
                    "voice_keywords": ["олег", "егоров", "продакт", "оунер"]
                }
            },
            
            "development": {
                "ulyanov_vladislav": {
                    "full_name": "Ульянов Владислав",
                    "role": "Team Lead команды разработки",
                    "team": "development",
                    "aliases": ["Владислав", "Влад", "Ульянов", "тимлид"],
                    "voice_keywords": ["владислав", "влад", "ульянов", "тимлид"]
                },
                "aloev_alexander": {
                    "full_name": "Алоев Александр",
                    "role": "Разработчик",
                    "team": "development",
                    "aliases": ["Александр", "Саша", "Алоев"],
                    "voice_keywords": ["александр", "саша", "алоев"]
                }
            },
            
            "testing": {
                "denchenko_yulia": {
                    "full_name": "Деньченко Юлия",
                    "role": "Team Lead команды тестирования",
                    "team": "testing",
                    "aliases": ["Юлия", "Юля", "Деньченко", "тимлид"],
                    "voice_keywords": ["юлия", "юля", "деньченко", "тимлид"]
                }
            }
        },
        
        "identification_rules": {
            "speaker_mapping": {
                "enabled": True,
                "auto_replace_speakers": True,
                "create_participant_summary": True
            },
            
            "matching_strategies": [
                {"strategy": "exact_name_match", "weight": 1.0, "description": "Точное совпадение полного имени"},
                {"strategy": "alias_match", "weight": 0.9, "description": "Совпадение с псевдонимом"},
                {"strategy": "voice_keyword_match", "weight": 0.8, "description": "Совпадение голосового ключевого слова"},
                {"strategy": "partial_name_match", "weight": 0.7, "description": "Частичное совпадение имени"},
                {"strategy": "role_context_match", "weight": 0.6, "description": "Совпадение по контексту роли"}
            ],
            
            "context_keywords": {
                "standup": {
                    "development": ["код", "разработка", "фича", "баг", "коммит"],
                    "testing": ["тест", "баг", "регрессия", "автотесты"],
                    "management": ["планы", "приоритеты", "релиз", "дедлайн"]
                }
            }
        },
        
        "output_formatting": {
            "use_full_names": True,
            "include_roles": False,
            "group_by_teams": True,
            "add_team_structure": True,
            "highlight_team_leads": True
        },
        
        "fallback_options": {
            "unknown_speaker_format": "Неизвестный участник {speaker_id}",
            "partial_match_confirmation": True,
            "suggest_similar_names": True,
            "confidence_warnings": True
        }
    }
    
    if not os.path.exists("team_config.json"):
        with open("team_config.json", "w", encoding="utf-8") as f:
            json.dump(sample_config, f, ensure_ascii=False, indent=2)
        print("✅ Создан образец конфигурации team_config.json")

def main():
    """Главная функция тестирования"""
    print("🧪 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ")
    print("=" * 50)
    
    # Проверяем наличие зависимостей
    try:
        from fuzzywuzzy import fuzz
        print("✅ fuzzywuzzy доступен")
    except ImportError:
        print("❌ fuzzywuzzy не установлен! Установите: pip install fuzzywuzzy")
        sys.exit(1)
    
    # Создаем образец конфигурации, если нет
    if not os.path.exists("team_config.json"):
        print("📝 Создаем образец конфигурации...")
        create_sample_config()
    
    # Запускаем тесты
    tester = SystemTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("Система готова к использованию.")
        print("\nДля демонстрации запустите:")
        print("python team_identification_demo.py")
        sys.exit(0)
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ!")
        print("Исправьте ошибки и запустите тестирование повторно.")
        sys.exit(1)

if __name__ == "__main__":
    main()