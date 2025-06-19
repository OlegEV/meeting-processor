#!/usr/bin/env python3
"""
Основной модуль системы обработки встреч
Объединяет все компоненты для транскрипции, идентификации команды и генерации протоколов
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

# Проверяем зависимости
def check_dependencies():
    """Проверяет наличие всех необходимых зависимостей"""
    missing_packages = []
    
    try:
        from deepgram import DeepgramClient, PrerecordedOptions
    except ImportError:
        missing_packages.append("deepgram-sdk")
    
    try:
        import anthropic
    except ImportError:
        missing_packages.append("anthropic")
    
    try:
        import requests
    except ImportError:
        missing_packages.append("requests")
    
    try:
        from fuzzywuzzy import fuzz
    except ImportError:
        missing_packages.append("fuzzywuzzy python-Levenshtein")
    
    if missing_packages:
        print("❌ Не удалось импортировать следующие пакеты:")
        for pkg in missing_packages:
            print(f"   {pkg}")
        print("\n💡 Установите недостающие пакеты:")
        print("   pip install deepgram-sdk anthropic requests fuzzywuzzy python-Levenshtein")
        return False
    
    return True

if not check_dependencies():
    sys.exit(1)

# Импортируем наши модули
try:
    from audio_processor import AudioProcessor
    from transcription_service import TranscriptionService
    from protocol_generator import ProtocolGenerator
    from file_utils import FileUtils
    from config_loader import ConfigLoader
except ImportError as e:
    print(f"❌ Ошибка импорта модулей системы: {e}")
    print("Убедитесь, что все файлы находятся в одной папке")
    sys.exit(1)

# Импортируем дополнительные модули
try:
    from meeting_templates import MeetingTemplates
except ImportError:
    MeetingTemplates = None

try:
    from team_identifier import TeamIdentifier
except ImportError:
    TeamIdentifier = None

try:
    from speaker_mapper import SpeakerMapper
except ImportError:
    SpeakerMapper = None

class MeetingProcessor:
    """Основной класс для обработки встреч"""
    
    def __init__(self, 
                 deepgram_api_key: str, 
                 claude_api_key: str, 
                 deepgram_timeout: int = 300,
                 claude_model: str = "claude-3-sonnet-20240229",
                 deepgram_options: dict = None,
                 chunk_duration_minutes: int = 10,
                 template_type: str = "standard",
                 templates_config_file: str = "templates_config.json",
                 team_config_file: str = "team_config.json",
                 progress_callback: Callable[[int, str], None] = None,
                 deepgram_max_retries: int = 3):
        """
        Инициализация процессора встреч
        
        Args:
            progress_callback: Функция для отправки прогресса (progress, message)
            deepgram_max_retries: Максимальное количество повторных попыток при таймауте Deepgram
        """
        # Инициализируем компоненты
        self.audio_processor = AudioProcessor()
        self.transcription_service = TranscriptionService(deepgram_api_key, deepgram_timeout, deepgram_options, deepgram_max_retries)
        self.protocol_generator = ProtocolGenerator(claude_api_key, claude_model)
        
        # Основные настройки
        self.chunk_duration_minutes = chunk_duration_minutes
        self.template_type = template_type
        self.progress_callback = progress_callback
        
        # Инициализация шаблонов протоколов
        self._initialize_templates(templates_config_file)
        
        # Инициализация идентификации команды
        self._initialize_team_identification(team_config_file)
        
        # Инициализация mapper'а спикеров
        self.speaker_mapper = SpeakerMapper(self.team_identifier) if SpeakerMapper else None
    
    def set_progress_callback(self, callback: Callable[[int, str], None]):
        """Устанавливает callback функцию для отслеживания прогресса"""
        self.progress_callback = callback
    
    def _update_progress(self, progress: int, message: str):
        """Обновляет прогресс через callback"""
        if self.progress_callback:
            self.progress_callback(progress, message)
        else:
            print(f"[{progress}%] {message}")
    
    def _initialize_templates(self, templates_config_file: str):
        """Инициализирует систему шаблонов"""
        if MeetingTemplates:
            try:
                self.templates = MeetingTemplates(templates_config_file)
            except Exception as e:
                self.templates = None
        else:
            self.templates = None
    
    def _initialize_team_identification(self, team_config_file: str):
        """Инициализирует систему идентификации команды"""
        if TeamIdentifier:
            try:
                self.team_identifier = TeamIdentifier(team_config_file)
            except Exception as e:
                self.team_identifier = None
        else:
            self.team_identifier = None
    
    def _print_initialization_info(self, deepgram_timeout: int, claude_model: str, deepgram_options: dict):
        """Выводит информацию о настройках"""
        print(f"\n🔧 НАСТРОЙКИ ПРОЦЕССОРА:")
        print(f"   ⏰ Таймаут Deepgram: {deepgram_timeout} сек")
        print(f"   🤖 Модель Claude: {claude_model}")
        print(f"   📝 Тип шаблона: {self.template_type}")
        print(f"   ✂️ Размер частей: {self.chunk_duration_minutes} мин")
        if deepgram_options:
            print(f"   🎤 Опции Deepgram: {', '.join([k for k, v in deepgram_options.items() if v])}")
    
    def process_meeting(self, 
                       input_file_path: str, 
                       output_dir: str = "output",
                       name_mapping: Optional[Dict[str, str]] = None,
                       keep_audio_file: bool = False,
                       template_type: str = None) -> bool:
        """
        Полный цикл обработки встречи с идентификацией команды
        """
        try:
            self._update_progress(5, "Инициализация обработки...")
            
            # Создаем выходную директорию
            Path(output_dir).mkdir(exist_ok=True)
            
            # Получаем информацию о файле
            self._update_progress(10, "Анализ входного файла...")
            file_type, file_ext, file_info = self.audio_processor.get_audio_info(input_file_path)
            file_datetime_info = FileUtils.get_file_datetime_info(input_file_path)
            
            # Подготавливаем пути для выходных файлов
            input_name = Path(input_file_path).stem
            transcript_path = f"{output_dir}/{input_name}_transcript.txt"
            summary_path = f"{output_dir}/{input_name}_summary.md"
            team_info_path = f"{output_dir}/{input_name}_team_info.txt"
            
            print(f"\n🎯 НАЧИНАЮ ОБРАБОТКУ ВСТРЕЧИ")
            print("=" * 50)
            print(f"📄 Файл: {input_file_path}")
            print(f"📊 Тип: {file_type} ({file_ext})")
            print(f"ℹ️  {file_info}")
            print(f"📅 Дата: {file_datetime_info['datetime_full']} ({file_datetime_info['weekday_ru']})")
            
            # Определяем тип шаблона
            if template_type is None:
                template_type = self.template_type
            print(f"📝 Шаблон: {template_type}")
            
            # Подготавливаем аудио для транскрипции
            self._update_progress(15, "Подготовка аудио файла...")
            audio_file_for_deepgram, temp_audio_created = self.audio_processor.prepare_audio_file(
                input_file_path, file_type, output_dir, input_name
            )
            
            if not audio_file_for_deepgram:
                self._update_progress(0, "Ошибка подготовки аудио файла")
                return False
            
            # Транскрибируем аудио
            self._update_progress(25, "Транскрибирование аудио...")
            transcript = self.transcription_service.transcribe_audio(audio_file_for_deepgram, self.chunk_duration_minutes)
            if transcript is None:
                self._update_progress(0, "Ошибка транскрибирования аудио")
                return False
            elif transcript == "":
                self._update_progress(30, "Файл содержит тишину или неразборчивую речь")
                # Создаем минимальный транскрипт для продолжения обработки
                transcript = "Файл содержит тишину или неразборчивую речь. Транскрипт пуст."
            
            # Генерируем протокол встречи СНАЧАЛА
            self._update_progress(50, "Генерация первичного протокола...")
            summary = self.protocol_generator.generate_meeting_summary(
                transcript, file_datetime_info, template_type, None, self.templates
            )
            if not summary:
                self._update_progress(0, "Ошибка генерации протокола")
                return False
            
            # Идентифицируем участников команды КОМПЛЕКСНО
            self._update_progress(65, "Идентификация участников...")
            team_identification = None
            final_transcript = transcript
            
            if self.team_identifier and self.speaker_mapper:
                # Анализируем протокол и транскрипт
                protocol_identification = self.team_identifier.identify_participants(summary, template_type)
                transcript_identification = self.team_identifier.identify_participants(transcript, template_type)
                
                # Создаем карту замен
                combined_replacements = self.speaker_mapper.create_combined_speaker_mapping(
                    transcript, summary, protocol_identification, transcript_identification
                )
                
                # Применяем замены к транскрипту
                if combined_replacements:
                    final_transcript = self.speaker_mapper.apply_speaker_replacements_to_transcript(
                        transcript, combined_replacements
                    )
                    
                    # Формируем итоговый объект team_identification
                    team_identification = self.speaker_mapper.create_final_team_identification(
                        combined_replacements, protocol_identification, transcript_identification
                    )
                else:
                    team_identification = transcript_identification
            
            # Сохраняем результаты
            self._update_progress(80, "Сохранение транскрипта...")
            FileUtils.save_transcript(transcript_path, final_transcript, file_datetime_info, template_type, team_identification)
            
            if team_identification and team_identification.get("identified", False):
                FileUtils.save_team_info(team_info_path, team_identification, file_datetime_info, input_file_path, template_type)
                
                # Регенерируем протокол с информацией о команде
                self._update_progress(90, "Генерация финального протокола с участниками...")
                summary = self.protocol_generator.generate_meeting_summary(
                    final_transcript, file_datetime_info, template_type, team_identification, self.templates
                )
            
            # Сохраняем финальный протокол
            self._update_progress(95, "Сохранение протокола...")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)
            
            # Очищаем временные файлы
            self._update_progress(98, "Очистка временных файлов...")
            FileUtils.cleanup_temp_files(temp_audio_created, audio_file_for_deepgram, keep_audio_file)
            
            self._update_progress(100, "Обработка завершена успешно!")
            return True
            
        except Exception as e:
            self._update_progress(0, f"Критическая ошибка: {str(e)}")
            print(f"❌ Критическая ошибка при обработке встречи: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_protocol_from_transcript(self, 
                                        transcript_file_path: str, 
                                        output_dir: str = "output",
                                        template_type: str = None) -> bool:
        """
        Генерирует протокол из готового транскрипта
        """
        try:
            self._update_progress(10, "Проверка файла транскрипта...")
            
            # Проверяем существование файла транскрипта
            if not os.path.exists(transcript_file_path):
                self._update_progress(0, f"Файл транскрипта не найден: {transcript_file_path}")
                return False
            
            # Создаем выходную директорию
            Path(output_dir).mkdir(exist_ok=True)
            
            # Читаем транскрипт
            self._update_progress(20, "Чтение транскрипта...")
            with open(transcript_file_path, "r", encoding="utf-8") as f:
                transcript = f.read()
            
            if not transcript.strip():
                self._update_progress(0, f"Транскрипт пустой: {transcript_file_path}")
                return False
            
            # Получаем информацию о файле транскрипта для даты
            file_datetime_info = FileUtils.get_file_datetime_info(transcript_file_path)
            
            # Определяем тип шаблона
            if template_type is None:
                template_type = self.template_type
            
            # Подготавливаем пути для выходных файлов
            input_name = Path(transcript_file_path).stem
            # Убираем суффикс _transcript если он есть
            if input_name.endswith("_transcript"):
                input_name = input_name[:-11]
            
            summary_path = f"{output_dir}/{input_name}_summary.md"
            team_info_path = f"{output_dir}/{input_name}_team_info.txt"
            
            print(f"🤖 Генерация протокола из: {transcript_file_path}")
            
            # Генерируем протокол встречи СНАЧАЛА
            self._update_progress(40, "Генерация первичного протокола...")
            summary = self.protocol_generator.generate_meeting_summary(
                transcript, file_datetime_info, template_type, None, self.templates
            )
            if not summary:
                self._update_progress(0, "Ошибка генерации протокола")
                return False
            
            # Идентифицируем участников команды КОМПЛЕКСНО
            self._update_progress(60, "Идентификация участников...")
            team_identification = None
            final_transcript = transcript
            
            if self.team_identifier and self.speaker_mapper:
                # Анализируем протокол и транскрипт
                protocol_identification = self.team_identifier.identify_participants(summary, template_type)
                transcript_identification = self.team_identifier.identify_participants(transcript, template_type)
                
                # Создаем карту замен
                combined_replacements = self.speaker_mapper.create_combined_speaker_mapping(
                    transcript, summary, protocol_identification, transcript_identification
                )
                
                # Применяем замены к транскрипту
                if combined_replacements:
                    final_transcript = self.speaker_mapper.apply_speaker_replacements_to_transcript(
                        transcript, combined_replacements
                    )
                    
                    # Формируем итоговый объект team_identification
                    team_identification = self.speaker_mapper.create_final_team_identification(
                        combined_replacements, protocol_identification, transcript_identification
                    )
                    
                    # Регенерируем протокол с информацией о команде
                    self._update_progress(80, "Генерация финального протокола с участниками...")
                    summary = self.protocol_generator.generate_meeting_summary(
                        final_transcript, file_datetime_info, template_type, team_identification, self.templates
                    )
                else:
                    team_identification = transcript_identification
            
            # Сохраняем результаты
            self._update_progress(90, "Сохранение результатов...")
            if team_identification and team_identification.get("identified", False):
                FileUtils.save_team_info(team_info_path, team_identification, file_datetime_info, transcript_file_path, template_type)
            
            # Обновляем транскрипт с заменами (если они были)
            if final_transcript != transcript:
                updated_transcript_path = f"{output_dir}/{input_name}_transcript_updated.txt"
                FileUtils.save_transcript(updated_transcript_path, final_transcript, file_datetime_info, template_type, team_identification)
            
            # Сохраняем финальный протокол
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)
            
            self._update_progress(100, "Протокол успешно сгенерирован!")
            
            print(f"✅ Протокол сохранен: {summary_path}")
            if team_identification and team_identification.get("identified", False):
                stats = team_identification.get("statistics", {})
                print(f"👥 Участников определено: {stats.get('total_identified', 0)}")
            
            return True
            
        except Exception as e:
            self._update_progress(0, f"Ошибка генерации протокола: {str(e)}")
            print(f"❌ Ошибка генерации протокола: {e}")
            return False
    
    def replace_speaker_names(self, transcript: str, name_mapping: Dict[str, str]) -> str:
        """Заменяет имена спикеров согласно маппингу (устаревший метод)"""
        if self.speaker_mapper:
            return self.speaker_mapper.replace_speaker_names_legacy(transcript, name_mapping)
        
        # Fallback если модуль недоступен
        if not name_mapping:
            return transcript
        
        modified_transcript = transcript
        for old_name, new_name in name_mapping.items():
            pattern = rf'\b{re.escape(old_name)}\b'
            modified_transcript = re.sub(pattern, new_name, modified_transcript, flags=re.IGNORECASE)
        
        return modified_transcript
    
    def transcribe_only(self, 
                       input_file_path: str, 
                       output_dir: str = "output",
                       keep_audio_file: bool = False) -> bool:
        """
        Только транскрибирует аудио без генерации протокола
        """
        try:
            self._update_progress(10, "Инициализация транскрибирования...")
            
            # Создаем выходную директорию
            Path(output_dir).mkdir(exist_ok=True)
            
            # Получаем информацию о файле
            self._update_progress(20, "Анализ входного файла...")
            file_type, file_ext, file_info = self.audio_processor.get_audio_info(input_file_path)
            file_datetime_info = FileUtils.get_file_datetime_info(input_file_path)
            
            # Подготавливаем пути для выходных файлов
            input_name = Path(input_file_path).stem
            transcript_path = f"{output_dir}/{input_name}_transcript.txt"
            
            print(f"🎤 Транскрибирование: {input_file_path}")
            
            # Подготавливаем аудио для транскрипции
            self._update_progress(30, "Подготовка аудио файла...")
            audio_file_for_deepgram, temp_audio_created = self.audio_processor.prepare_audio_file(
                input_file_path, file_type, output_dir, input_name
            )
            
            if not audio_file_for_deepgram:
                self._update_progress(0, "Ошибка подготовки аудио файла")
                return False
            
            # Транскрибируем аудио
            self._update_progress(50, "Транскрибирование аудио...")
            transcript = self.transcription_service.transcribe_audio(audio_file_for_deepgram, self.chunk_duration_minutes)
            if transcript is None:
                self._update_progress(0, "Ошибка транскрибирования аудио")
                return False
            elif transcript == "":
                self._update_progress(60, "Файл содержит тишину или неразборчивую речь")
                # Создаем минимальный транскрипт для сохранения
                transcript = "Файл содержит тишину или неразборчивую речь. Транскрипт пуст."
            
            # Сохраняем транскрипт
            self._update_progress(90, "Сохранение транскрипта...")
            FileUtils.save_transcript(transcript_path, transcript, file_datetime_info, "transcription_only", None)
            
            # Очищаем временные файлы
            self._update_progress(95, "Очистка временных файлов...")
            FileUtils.cleanup_temp_files(temp_audio_created, audio_file_for_deepgram, keep_audio_file)
            
            self._update_progress(100, "Транскрибирование завершено!")
            print(f"✅ Транскрипт сохранен: {transcript_path}")
            return True
            
        except Exception as e:
            self._update_progress(0, f"Ошибка транскрибирования: {str(e)}")
            print(f"❌ Ошибка транскрибирования: {e}")
            return False
    
    def _print_completion_summary(self, output_dir: str, template_type: str, team_identification: Dict):
        """Выводит итоговую информацию об обработке"""
        print(f"✅ Обработка завершена: {output_dir}")
        if team_identification and team_identification.get("identified", False):
            stats = team_identification.get("statistics", {})
            print(f"👥 Участников определено: {stats.get('total_identified', 0)}")

def main():
    """Основная функция командной строки"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Система обработки встреч с транскрипцией, идентификацией команды и генерацией протоколов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

Полная обработка:
  python meeting_processor_fixed.py meeting.mp4
  python meeting_processor_fixed.py meeting.mp3 --template standup

Только транскрибирование:
  python meeting_processor_fixed.py meeting.mp4 --transcribe-only
  python meeting_processor_fixed.py meeting.mp3 --transcribe-only --output transcripts

Только генерация протокола:
  python meeting_processor_fixed.py --protocol-only meeting_transcript.txt
  python meeting_processor_fixed.py --protocol-only meeting_transcript.txt --template standup --output protocols

Настройки:
  python meeting_processor_fixed.py meeting.mp4 --timeout 600 --chunks 10 --template standup
        """
    )
    
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Путь к входному файлу (видео или аудио)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Директория для сохранения результатов"
    )
    
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Путь к файлу конфигурации"
    )
    
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        help="Таймаут для Deepgram в секундах"
    )
    
    parser.add_argument(
        "--chunks",
        type=int,
        help="Размер частей в минутах"
    )
    
    parser.add_argument(
        "--template",
        help="Тип шаблона протокола"
    )
    
    parser.add_argument(
        "--transcribe-only",
        action="store_true",
        help="Только транскрибировать аудио без генерации протокола"
    )
    
    parser.add_argument(
        "--protocol-only",
        help="Сгенерировать протокол из готового транскрипта (укажите путь к файлу)"
    )
    
    args = parser.parse_args()
    
    # Только транскрибирование
    if args.transcribe_only:
        # Загружаем конфигурацию
        config = ConfigLoader.load_config(args.config)
        if not config:
            print(f"❌ Не удалось загрузить конфигурацию из {args.config}")
            return
        
        # Получаем настройки
        settings = ConfigLoader.get_settings_from_config(config, args)
        
        # Проверяем входной файл
        if not os.path.exists(settings['input_file']):
            print(f"❌ Файл не найден: {settings['input_file']}")
            return
        
        # Загружаем и проверяем API ключ Deepgram
        api_keys_data = ConfigLoader.load_api_keys(settings['api_keys_file'])
        deepgram_valid, _, deepgram_key, _ = ConfigLoader.validate_api_keys(api_keys_data)
        
        if not deepgram_valid:
            print(f"❌ Не настроен API ключ для Deepgram")
            return
        
        # Создаем процессор только для транскрибирования
        processor = MeetingProcessor(
            deepgram_api_key=deepgram_key,
            claude_api_key="dummy",  # Не нужен для транскрибирования
            deepgram_timeout=settings['deepgram_timeout'],
            chunk_duration_minutes=settings['chunk_minutes']
        )
        
        success = processor.transcribe_only(
            input_file_path=settings['input_file'],
            output_dir=settings['output_dir'],
            keep_audio_file=settings['keep_audio']
        )
        
        return 0 if success else 1
    
    # Только генерация протокола
    if args.protocol_only:
        # Загружаем конфигурацию
        config = ConfigLoader.load_config(args.config)
        if not config:
            print(f"❌ Не удалось загрузить конфигурацию из {args.config}")
            return
        
        # Получаем настройки
        settings = ConfigLoader.get_settings_from_config(config, args)
        
        # Загружаем и проверяем API ключ Claude
        api_keys_data = ConfigLoader.load_api_keys(settings['api_keys_file'])
        _, claude_valid, _, claude_key = ConfigLoader.validate_api_keys(api_keys_data)
        
        if not claude_valid:
            print(f"❌ Не настроен API ключ для Claude")
            return
        
        # Создаем процессор только для генерации протокола
        processor = MeetingProcessor(
            deepgram_api_key="dummy",  # Не нужен для генерации протокола
            claude_api_key=claude_key,
            claude_model=settings['claude_model'],
            template_type=settings['template_type'],
            templates_config_file=settings['templates_config'],
            team_config_file=settings['team_config']
        )
        
        success = processor.generate_protocol_from_transcript(
            transcript_file_path=args.protocol_only,
            output_dir=settings['output_dir'],
            template_type=settings['template_type']
        )
        
        return 0 if success else 1
    
    # Полная обработка (по умолчанию)
    
    # Загружаем конфигурацию
    config = ConfigLoader.load_config(args.config)
    if not config:
        print(f"❌ Не удалось загрузить конфигурацию из {args.config}")
        return
    
    # Получаем настройки
    settings = ConfigLoader.get_settings_from_config(config, args)
    
    # Проверяем входной файл
    if not os.path.exists(settings['input_file']):
        print(f"\n❌ Файл не найден: {settings['input_file']}")
        return
    
    # Загружаем и проверяем API ключи
    api_keys_data = ConfigLoader.load_api_keys(settings['api_keys_file'])
    deepgram_valid, claude_valid, deepgram_key, claude_key = ConfigLoader.validate_api_keys(api_keys_data)
    
    if not deepgram_valid:
        print(f"\n❌ Не настроен API ключ для Deepgram")
        return
    
    if not claude_valid:
        print(f"\n❌ Не настроен API ключ для Claude")
        return
    
    # Создаем и запускаем процессор
    try:
        processor = MeetingProcessor(
            deepgram_api_key=deepgram_key,
            claude_api_key=claude_key,
            deepgram_timeout=settings['deepgram_timeout'],
            claude_model=settings['claude_model'],
            deepgram_options=settings['deepgram_options'],
            chunk_duration_minutes=settings['chunk_minutes'],
            template_type=settings['template_type'],
            templates_config_file=settings['templates_config'],
            team_config_file=settings['team_config']
        )
        
        success = processor.process_meeting(
            input_file_path=settings['input_file'],
            output_dir=settings['output_dir'],
            keep_audio_file=settings['keep_audio'],
            template_type=settings['template_type']
        )
        
        if success:
            print(f"\n🎉 ВСЯ ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО!")
        else:
            print(f"\n❌ Обработка завершилась с ошибками")
            return 1
            
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
