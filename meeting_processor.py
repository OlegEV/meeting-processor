#!/usr/bin/env python3
"""
Основной модуль системы обработки встреч
Объединяет все компоненты для транскрипции и генерации протоколов
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

# Проверяем зависимости
def check_dependencies():
    """Проверяет наличие всех необходимых зависимостей"""
    missing_packages = []
    
    try:
        from deepgram import DeepgramClient
    except ImportError:
        missing_packages.append("deepgram-sdk")
    
    try:
        import openai
    except ImportError:
        missing_packages.append("openai")
    
    try:
        import requests
    except ImportError:
        missing_packages.append("requests")
    
    if missing_packages:
        print("❌ Не удалось импортировать следующие пакеты:")
        for pkg in missing_packages:
            print(f"   {pkg}")
        print("\n💡 Установите недостающие пакеты:")
        print("   pip install deepgram-sdk anthropic requests")
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
                 progress_callback: Callable[[int, str], None] = None,
                 deepgram_max_retries: int = 3,
                 deepgram_language: str = "ru",
                 deepgram_model: str = "nova-3",
                 deepgram_proxy: dict = None):
        """
        Инициализация процессора встреч

        Args:
            progress_callback: Функция для отправки прогресса (progress, message)
            deepgram_max_retries: Максимальное количество повторных попыток при таймауте Deepgram
            deepgram_language: Язык для транскрипции Deepgram
            deepgram_model: Модель Deepgram для транскрипции
            deepgram_proxy: Настройки прокси для Deepgram (settings.deepgram_proxy)
        """
        self.audio_processor = AudioProcessor()
        self.transcription_service = TranscriptionService(
            deepgram_api_key,
            deepgram_timeout,
            deepgram_options,
            deepgram_max_retries,
            deepgram_language,
            deepgram_model,
            deepgram_proxy
        )
        self.protocol_generator = ProtocolGenerator(claude_api_key, claude_model)

        self.chunk_duration_minutes = chunk_duration_minutes
        self.template_type = template_type
        self.progress_callback = progress_callback

        self._initialize_templates(templates_config_file)

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
                       keep_audio_file: bool = False,
                       template_type: str = None,
                       temp_dir: Optional[str] = None,
                       participants: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        Полный цикл обработки встречи.

        temp_dir — отдельный каталог для промежуточных аудио-файлов (.wav и chunk'и).
        Если не задан, используется output_dir (legacy-поведение).
        """
        try:
            self._update_progress(5, "Инициализация обработки...")

            Path(output_dir).mkdir(exist_ok=True)
            if temp_dir:
                Path(temp_dir).mkdir(parents=True, exist_ok=True)

            self._update_progress(10, "Анализ входного файла...")
            file_type, file_ext, file_info = self.audio_processor.get_audio_info(input_file_path)
            file_datetime_info = FileUtils.get_file_datetime_info(input_file_path)

            input_name = Path(input_file_path).stem
            transcript_path = f"{output_dir}/{input_name}_transcript.txt"
            summary_path = f"{output_dir}/{input_name}_summary.md"

            print(f"\n🎯 НАЧИНАЮ ОБРАБОТКУ ВСТРЕЧИ")
            print("=" * 50)
            print(f"📄 Файл: {input_file_path}")
            print(f"📊 Тип: {file_type} ({file_ext})")
            print(f"ℹ️  {file_info}")
            print(f"📅 Дата: {file_datetime_info['datetime_full']} ({file_datetime_info['weekday_ru']})")

            if template_type is None:
                template_type = self.template_type
            print(f"📝 Шаблон: {template_type}")

            self._update_progress(15, "Подготовка аудио файла...")
            audio_file_for_deepgram, temp_audio_created = self.audio_processor.prepare_audio_file(
                input_file_path, file_type, output_dir, input_name, temp_dir=temp_dir
            )

            if not audio_file_for_deepgram:
                self._update_progress(0, "Ошибка подготовки аудио файла")
                return False

            self._update_progress(25, "Транскрибирование аудио...")
            transcript = self.transcription_service.transcribe_audio(
                audio_file_for_deepgram, self.chunk_duration_minutes, chunk_output_dir=temp_dir
            )
            if transcript is None:
                self._update_progress(0, "Ошибка транскрибирования аудио")
                return False
            elif transcript == "":
                self._update_progress(30, "Файл содержит тишину или неразборчивую речь")
                transcript = "Файл содержит тишину или неразборчивую речь. Транскрипт пуст."

            self._update_progress(50, "Генерация протокола...")
            summary = self.protocol_generator.generate_meeting_summary(
                transcript, file_datetime_info, template_type, self.templates, participants
            )
            if not summary:
                self._update_progress(0, "Ошибка генерации протокола")
                return False

            self._update_progress(80, "Сохранение транскрипта...")
            FileUtils.save_transcript(transcript_path, transcript, file_datetime_info, template_type)

            self._update_progress(95, "Сохранение протокола...")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)

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
                                        template_type: str = None,
                                        participants: Optional[List[Dict[str, str]]] = None) -> bool:
        """Генерирует протокол из готового транскрипта"""
        try:
            self._update_progress(10, "Проверка файла транскрипта...")

            if not os.path.exists(transcript_file_path):
                self._update_progress(0, f"Файл транскрипта не найден: {transcript_file_path}")
                return False

            Path(output_dir).mkdir(exist_ok=True)

            self._update_progress(20, "Чтение транскрипта...")
            transcript = FileUtils.load_transcript(transcript_file_path)

            if not transcript.strip():
                self._update_progress(0, f"Транскрипт пустой: {transcript_file_path}")
                return False

            file_datetime_info = FileUtils.get_file_datetime_info(transcript_file_path)

            if template_type is None:
                template_type = self.template_type

            input_name = Path(transcript_file_path).stem
            if input_name.endswith("_transcript"):
                input_name = input_name[:-11]

            summary_path = f"{output_dir}/{input_name}_summary.md"

            print(f"🤖 Генерация протокола из: {transcript_file_path}")

            self._update_progress(40, "Генерация протокола...")
            summary = self.protocol_generator.generate_meeting_summary(
                transcript, file_datetime_info, template_type, self.templates, participants
            )
            if not summary:
                self._update_progress(0, "Ошибка генерации протокола")
                return False

            self._update_progress(90, "Сохранение результатов...")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)

            self._update_progress(100, "Протокол успешно сгенерирован!")
            print(f"✅ Протокол сохранен: {summary_path}")
            return True

        except Exception as e:
            self._update_progress(0, f"Ошибка генерации протокола: {str(e)}")
            print(f"❌ Ошибка генерации протокола: {e}")
            return False

    def transcribe_only(self,
                       input_file_path: str,
                       output_dir: str = "output",
                       keep_audio_file: bool = False,
                       temp_dir: Optional[str] = None) -> bool:
        """
        Только транскрибирует аудио без генерации протокола.

        temp_dir — отдельный каталог для промежуточных аудио-файлов (.wav и chunk'и).
        """
        try:
            self._update_progress(10, "Инициализация транскрибирования...")

            # Создаем выходную директорию
            Path(output_dir).mkdir(exist_ok=True)
            if temp_dir:
                Path(temp_dir).mkdir(parents=True, exist_ok=True)

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
                input_file_path, file_type, output_dir, input_name, temp_dir=temp_dir
            )

            if not audio_file_for_deepgram:
                self._update_progress(0, "Ошибка подготовки аудио файла")
                return False

            # Транскрибируем аудио
            self._update_progress(50, "Транскрибирование аудио...")
            transcript = self.transcription_service.transcribe_audio(
                audio_file_for_deepgram, self.chunk_duration_minutes, chunk_output_dir=temp_dir
            )
            if transcript is None:
                self._update_progress(0, "Ошибка транскрибирования аудио")
                return False
            elif transcript == "":
                self._update_progress(60, "Файл содержит тишину или неразборчивую речь")
                # Создаем минимальный транскрипт для сохранения
                transcript = "Файл содержит тишину или неразборчивую речь. Транскрипт пуст."
            
            # Сохраняем транскрипт
            self._update_progress(90, "Сохранение транскрипта...")
            FileUtils.save_transcript(transcript_path, transcript, file_datetime_info, "transcription_only")

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

def main():
    """Основная функция командной строки"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Система обработки встреч с транскрипцией и генерацией протоколов",
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
            chunk_duration_minutes=settings['chunk_minutes'],
            deepgram_language=settings.get('deepgram_language', 'ru'),
            deepgram_model=settings.get('deepgram_model', 'nova-2'),
            deepgram_proxy=settings.get('deepgram_proxy')
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
            templates_config_file=settings['templates_config']
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
            deepgram_language=settings.get('deepgram_language', 'ru'),
            deepgram_model=settings.get('deepgram_model', 'nova-2'),
            deepgram_proxy=settings.get('deepgram_proxy')
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
