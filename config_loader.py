#!/usr/bin/env python3
"""
Загрузчик конфигурационных файлов
"""

import os
import json
from typing import Dict

class ConfigLoader:
    """Класс для загрузки различных конфигурационных файлов"""
    
    @staticmethod
    def load_api_keys(api_keys_file: str = None) -> Dict:
        """Загружает API ключи из переменных окружения"""
        # Получаем ключи из переменных окружения
        deepgram_key = os.getenv('DEEPGRAM_API_KEY', '')
        claude_key = os.getenv('CLAUDE_API_KEY', '')
        
        if not deepgram_key:
            print("⚠️ Переменная окружения DEEPGRAM_API_KEY не установлена")
        
        if not claude_key:
            print("⚠️ Переменная окружения CLAUDE_API_KEY не установлена")
        
        return {
            "api_keys": {
                "deepgram": deepgram_key,
                "claude": claude_key
            }
        }

    @staticmethod
    def load_config(config_file: str = "config.json") -> Dict:
        """Загружает основную конфигурацию из файла"""
        try:
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print(f"❌ Файл конфигурации {config_file} не найден")
                return {}
        except Exception as e:
            print(f"❌ Ошибка при загрузке конфигурации: {e}")
            return {}

    @staticmethod
    def load_name_mapping(config_file: str = "names_config.json") -> Dict[str, str]:
        """Загружает конфигурацию замен имен из файла (устаревший метод)"""
        try:
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                default_mapping = {
                    "Speaker 0": "Участник 1",
                    "Speaker 1": "Участник 2", 
                    "Speaker 2": "Участник 3"
                }
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(default_mapping, f, ensure_ascii=False, indent=2)
                print(f"📁 Создан файл конфигурации {config_file}")
                return default_mapping
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке конфигурации имен: {e}")
            return {}
    
    @staticmethod
    def validate_api_keys(api_keys: Dict) -> tuple:
        """Проверяет корректность API ключей"""
        deepgram_key = api_keys.get("api_keys", {}).get("deepgram", "")
        claude_key = api_keys.get("api_keys", {}).get("claude", "")
        
        deepgram_valid = deepgram_key and deepgram_key != "your_deepgram_api_key_here"
        claude_valid = claude_key and claude_key not in ["your_claude_api_key_here", "your_openrouter_api_key_here"]
        
        return deepgram_valid, claude_valid, deepgram_key, claude_key
    
    @staticmethod
    def get_settings_from_config(config: Dict, args=None) -> Dict:
        """Извлекает настройки из конфигурации с учетом аргументов командной строки"""
        settings = {}
        
        # Пути к файлам
        settings['input_file'] = getattr(args, 'input_file', None) or config.get("paths", {}).get("input_file", "meeting.mp4")
        settings['output_dir'] = getattr(args, 'output', None) or config.get("paths", {}).get("output_dir", "meeting_output")
        settings['names_config'] = getattr(args, 'names', None) or config.get("paths", {}).get("names_config", "names_config.json")
        settings['templates_config'] = config.get("paths", {}).get("templates_config", "templates_config.json")
        settings['team_config'] = getattr(args, 'team_config', None) or config.get("paths", {}).get("team_config", "team_config.json")
        # API keys are now loaded from environment variables only
        settings['api_keys_file'] = None
        
        # Настройки обработки
        settings['deepgram_timeout'] = getattr(args, 'timeout', None) or config.get("settings", {}).get("deepgram_timeout_seconds", 300)
        settings['chunk_minutes'] = getattr(args, 'chunks', None) or config.get("settings", {}).get("chunk_duration_minutes", 10)
        settings['keep_audio'] = getattr(args, 'keep_audio', False) or config.get("settings", {}).get("keep_audio_file", False)
        settings['claude_model'] = getattr(args, 'claude_model', None) or config.get("settings", {}).get("claude_model", "claude-3-sonnet-20240229")
        settings['template_type'] = getattr(args, 'template', None) or config.get("settings", {}).get("template_type", "standard")
        
        # Настройки Deepgram
        settings['deepgram_language'] = config.get("settings", {}).get("language", "ru")
        settings['deepgram_model'] = config.get("settings", {}).get("deepgram_model", "nova-3")
        settings['deepgram_proxy'] = config.get("settings", {}).get("deepgram_proxy", {})
        
        # Опции Deepgram
        settings['deepgram_options'] = config.get("deepgram_options", {})
        
        return settings
