#!/usr/bin/env python3
"""
Telegram бот для обработки встреч с поддержкой URL и облачных сервисов
Версия: 2.1 с полной поддержкой HTTP ссылок и отслеживания прогресса
"""

import os
import sys
import json
import asyncio
import tempfile
import shutil
import traceback
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

# Telegram bot imports
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
    from telegram.constants import ParseMode, ChatAction
    from telegram.error import TelegramError
except ImportError:
    print("❌ Установите python-telegram-bot:")
    print("pip install python-telegram-bot")
    sys.exit(1)

# Наши модули
try:
    from meeting_processor import MeetingProcessor
except ImportError:
    print("❌ Не найден модуль meeting_processor.py")
    print("Убедитесь, что файл meeting_processor.py находится в той же папке")
    sys.exit(1)

try:
    from url_file_processor import URLFileProcessor, URLValidator
    URL_PROCESSOR_AVAILABLE = True
except ImportError:
    print("⚠️ Модуль url_file_processor.py не найден - URL обработка будет отключена")
    URLFileProcessor = None
    URLValidator = None
    URL_PROCESSOR_AVAILABLE = False

# Настройка логирования
def setup_logging(log_level: str = "INFO", log_file: str = "telegram_bot.log"):
    """Настраивает систему логирования"""
    from logging.handlers import RotatingFileHandler
    
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Создаем папку для логов
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", log_file)
    
    handlers = [
        RotatingFileHandler(log_path, maxBytes=100*1024*1024, backupCount=3, encoding='utf-8'),
        logging.StreamHandler()
    ]
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger(__name__)

class FileValidator:
    """Валидатор загружаемых файлов"""
    
    SUPPORTED_FORMATS = {
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.opus', '.wma'],
        'video': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm', '.flv']
    }
    
    @classmethod
    def validate_file(cls, file_obj, max_size_mb: int) -> Tuple[bool, str]:
        """Валидирует файл"""
        if not file_obj:
            return False, "Не удалось получить информацию о файле"
        
        # Проверяем размер
        if hasattr(file_obj, 'file_size') and file_obj.file_size:
            file_size_mb = file_obj.file_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                return False, f"Файл слишком большой: {file_size_mb:.1f} МБ (максимум {max_size_mb} МБ)"
        
        # Проверяем формат
        filename = getattr(file_obj, 'file_name', '') or f"file_{getattr(file_obj, 'file_id', 'unknown')}"
        file_ext = Path(filename).suffix.lower()
        
        all_formats = cls.SUPPORTED_FORMATS['audio'] + cls.SUPPORTED_FORMATS['video']
        if file_ext and file_ext not in all_formats:
            return False, (
                f"Неподдерживаемый формат: `{file_ext}`\n\n"
                f"Поддерживаемые форматы:\n"
                f"🎵 Аудио: {', '.join(cls.SUPPORTED_FORMATS['audio']).upper()}\n"
                f"🎬 Видео: {', '.join(cls.SUPPORTED_FORMATS['video']).upper()}"
            )
        
        return True, ""
    
    @classmethod
    def get_file_type(cls, filename: str) -> str:
        """Определяет тип файла"""
        file_ext = Path(filename).suffix.lower()
        if file_ext in cls.SUPPORTED_FORMATS['audio']:
            return 'audio'
        elif file_ext in cls.SUPPORTED_FORMATS['video']:
            return 'video'
        return 'unknown'

class UserSession:
    """Класс для управления пользовательскими сессиями"""
    
    def __init__(self, user_id: int, default_template: str = "standard"):
        self.user_id = user_id
        self.template = default_template
        self.processing = False
        self.current_file = None
        self.processing_start_time = None
        self.last_activity = datetime.now()
        self.current_progress = 0
        self.current_message = ""
        self.status_message_id = None  # ID сообщения со статусом для обновления
    
    def start_processing(self, filename: str):
        """Начинает обработку файла"""
        self.processing = True
        self.current_file = filename
        self.processing_start_time = datetime.now()
        self.last_activity = datetime.now()
        self.current_progress = 0
        self.current_message = "Начало обработки..."
        self.status_message_id = None
    
    def update_progress(self, progress: int, message: str):
        """Обновляет прогресс обработки"""
        self.current_progress = progress
        self.current_message = message
        self.last_activity = datetime.now()
    
    def stop_processing(self):
        """Завершает обработку"""
        self.processing = False
        self.current_file = None
        self.processing_start_time = None
        self.last_activity = datetime.now()
        self.current_progress = 0
        self.current_message = ""
        self.status_message_id = None
    
    def get_processing_duration(self) -> Optional[int]:
        """Возвращает длительность обработки в секундах"""
        if self.processing_start_time:
            return int((datetime.now() - self.processing_start_time).total_seconds())
        return None

class MeetingBot:
    """Основной класс Telegram бота для обработки встреч"""
    
    def __init__(self, config_file: str = "bot_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.logger = setup_logging(
            self.config.get("logging", {}).get("log_level", "INFO"),
            self.config.get("logging", {}).get("log_file", "telegram_bot.log")
        )
        
        # Инициализируем хранилища
        self.user_sessions: Dict[int, UserSession] = {}
        
        # Хранилище для URL с короткими ID
        self.url_storage: Dict[str, str] = {}  # short_id -> url
        self.url_counter = 0
        
        # Загружаем API ключи
        self.api_keys = self._load_api_keys()
        
        # Инициализируем URL процессор
        self._initialize_url_processor()
        
        # Статистика
        self.stats = {
            'total_files_processed': 0,
            'total_urls_processed': 0,
            'total_errors': 0,
            'active_users': set(),
            'start_time': datetime.now()
        }
        
        self.logger.info("🤖 MeetingBot инициализирован")
    
    def _create_short_url_id(self, url: str) -> str:
        """Создает короткий ID для URL"""
        self.url_counter += 1
        short_id = f"url_{self.url_counter}"
        self.url_storage[short_id] = url
        return short_id
    
    def _get_url_by_id(self, short_id: str) -> Optional[str]:
        """Получает URL по короткому ID"""
        return self.url_storage.get(short_id)
    
    def _load_config(self) -> Dict:
        """Загружает конфигурацию бота"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = self._create_default_config()
                self._save_config(config)
                print(f"📁 Создан файл конфигурации {self.config_file}")
            
            return config
            
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            return self._create_default_config()
    
    def _save_config(self, config: Dict):
        """Сохраняет конфигурацию в файл"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Ошибка сохранения конфигурации: {e}")
    
    def _create_default_config(self) -> Dict:
        """Создает конфигурацию по умолчанию"""
        return {
            "telegram": {
                "allowed_users": [],
                "admin_users": [],
                "max_file_size_mb": 100
            },
            "processing": {
                "default_template": "standard",
                "max_concurrent_jobs": 3,
                "processing_timeout": 1800,
                "deepgram_timeout": 300,
                "chunk_duration_minutes": 15,
                "progress_update_interval": 5  # Интервал обновления прогресса в секундах
            },
            "url_processing": {
                "enabled": True,
                "max_file_size_mb": 500,
                "download_timeout_seconds": 1800,
                "auto_detect_links": True,
                "cloud_services": {
                    "google_drive": True,
                    "yandex_disk": True
                }
            },
            "notifications": {
                "send_progress_updates": True,
                "notify_on_completion": True,
                "notify_on_error": True
            },
            "logging": {
                "log_level": "INFO",
                "log_file": "telegram_bot.log"
            }
        }
    
    def _load_api_keys(self) -> Dict:
        """Загружает API ключи из переменных окружения"""
        api_keys = {}
        
        # Загружаем из переменных окружения
        env_deepgram = os.getenv('DEEPGRAM_API_KEY')
        env_claude = os.getenv('CLAUDE_API_KEY')
        env_telegram = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if env_deepgram:
            api_keys['deepgram'] = env_deepgram
            if hasattr(self, 'logger'):
                self.logger.info("🔑 Использован Deepgram API ключ из переменной окружения")
        else:
            if hasattr(self, 'logger'):
                self.logger.warning("⚠️ Переменная окружения DEEPGRAM_API_KEY не установлена")
        
        if env_claude:
            api_keys['claude'] = env_claude
            if hasattr(self, 'logger'):
                self.logger.info("🔑 Использован Claude API ключ из переменной окружения")
        else:
            if hasattr(self, 'logger'):
                self.logger.warning("⚠️ Переменная окружения CLAUDE_API_KEY не установлена")
        
        if env_telegram:
            api_keys['telegram_bot_token'] = env_telegram
            if hasattr(self, 'logger'):
                self.logger.info("🔑 Использован Telegram Bot токен из переменной окружения")
        else:
            if hasattr(self, 'logger'):
                self.logger.warning("⚠️ Переменная окружения TELEGRAM_BOT_TOKEN не установлена")
        
        return {"api_keys": api_keys}
    
    def _initialize_url_processor(self):
        """Инициализирует URL процессор"""
        url_config = self.config.get("url_processing", {})
        
        if URL_PROCESSOR_AVAILABLE and url_config.get("enabled", True):
            try:
                max_size = url_config.get("max_file_size_mb", 500)
                timeout = url_config.get("download_timeout_seconds", 1800)
                
                self.url_processor = URLFileProcessor(max_size, timeout)
                self.url_validator = URLValidator()
                
                self.logger.info("✅ URL процессор инициализирован")
            except Exception as e:
                self.logger.error(f"❌ Ошибка инициализации URL процессора: {e}")
                self.url_processor = None
                self.url_validator = None
        else:
            self.url_processor = None
            self.url_validator = None
            if not URL_PROCESSOR_AVAILABLE:
                self.logger.info("⚠️ URL процессор недоступен - модуль не найден")
            else:
                self.logger.info("⚠️ URL обработка отключена в конфигурации")
    
    def get_user_session(self, user_id: int) -> UserSession:
        """Получает или создает сессию пользователя"""
        if user_id not in self.user_sessions:
            default_template = self.config.get("processing", {}).get("default_template", "standard")
            self.user_sessions[user_id] = UserSession(user_id, default_template)
            self.stats['active_users'].add(user_id)
        return self.user_sessions[user_id]
    
    def is_user_allowed(self, user_id: int) -> bool:
        """Проверяет права доступа пользователя"""
        allowed_users = self.config.get("telegram", {}).get("allowed_users", [])
        return len(allowed_users) == 0 or user_id in allowed_users
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет права администратора"""
        admin_users = self.config.get("telegram", {}).get("admin_users", [])
        return user_id in admin_users
    
    def _validate_api_keys(self) -> Tuple[bool, str]:
        """Проверяет наличие необходимых API ключей"""
        api_keys = self.api_keys.get("api_keys", {})
        
        if not api_keys.get("deepgram"):
            return False, "❌ API ключ Deepgram не настроен"
        
        if not api_keys.get("claude"):
            return False, "❌ API ключ Claude не настроен"
        
        return True, ""
    
    def _create_progress_callback(self, user_session: UserSession, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Создает callback функцию для обновления прогресса"""
        last_update_time = 0
        update_interval = self.config.get("processing", {}).get("progress_update_interval", 5)
        
        async def progress_callback(progress: int, message: str):
            nonlocal last_update_time
            
            # Обновляем сессию
            user_session.update_progress(progress, message)
            
            # Проверяем, нужно ли отправлять обновление в Telegram
            current_time = datetime.now().timestamp()
            send_progress_updates = self.config.get("notifications", {}).get("send_progress_updates", True)
            
            # Отправляем обновление если:
            # 1. Включены уведомления о прогрессе
            # 2. Прошло достаточно времени с последнего обновления ИЛИ это завершение (100%)
            # 3. Это важные этапы (кратные 25% или завершение)
            should_update = (
                send_progress_updates and 
                (current_time - last_update_time >= update_interval or progress == 100 or progress == 0) and
                (progress % 25 == 0 or progress == 100 or progress == 0)
            )
            
            if should_update:
                try:
                    # Создаем прогресс-бар
                    progress_bar = self._create_progress_bar(progress)
                    duration = user_session.get_processing_duration()
                    duration_text = f" ({duration}с)" if duration else ""
                    
                    status_text = (
                        f"🔄 *Обработка файла*\n\n"
                        f"{progress_bar}\n"
                        f"📊 Прогресс: {progress}%\n"
                        f"📝 Этап: {message}\n"
                        f"⏱️ Время: {duration_text}\n"
                        f"📁 Файл: `{user_session.current_file}`"
                    )
                    
                    if progress == 100:
                        status_text = (
                            f"✅ *Обработка завершена!*\n\n"
                            f"{progress_bar}\n"
                            f"📁 Файл: `{user_session.current_file}`\n"
                            f"⏱️ Общее время: {duration_text}\n\n"
                            f"📎 Файлы будут отправлены в ближайшее время..."
                        )
                    elif progress == 0:
                        status_text = (
                            f"❌ *Ошибка обработки*\n\n"
                            f"📁 Файл: `{user_session.current_file}`\n"
                            f"💬 Ошибка: {message}\n\n"
                            f"Попробуйте еще раз или обратитесь к администратору."
                        )
                    
                    # Отправляем или обновляем сообщение
                    if user_session.status_message_id:
                        try:
                            await context.bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=user_session.status_message_id,
                                text=status_text,
                                parse_mode=ParseMode.MARKDOWN
                            )
                        except Exception:
                            # Если не удалось обновить, отправляем новое
                            message = await context.bot.send_message(
                                chat_id=chat_id,
                                text=status_text,
                                parse_mode=ParseMode.MARKDOWN
                            )
                            user_session.status_message_id = message.message_id
                    else:
                        # Отправляем новое сообщение
                        message = await context.bot.send_message(
                            chat_id=chat_id,
                            text=status_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        user_session.status_message_id = message.message_id
                    
                    last_update_time = current_time
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка отправки обновления прогресса: {e}")
        
        # Создаем синхронную версию для совместимости
        def sync_progress_callback(progress: int, message: str):
            try:
                import asyncio as aio
                # Получаем текущий event loop
                try:
                    loop = aio.get_running_loop()
                    # Если loop уже запущен, создаем task
                    loop.create_task(progress_callback(progress, message))
                except RuntimeError:
                    # Если нет запущенного loop, создаем новый
                    aio.run(progress_callback(progress, message))
            except Exception as e:
                self.logger.error(f"❌ Ошибка в sync_progress_callback: {e}")
        
        # Возвращаем объект с обеими версиями
        progress_callback.sync = sync_progress_callback
        return progress_callback
    
    def _create_progress_bar(self, progress: int, length: int = 20) -> str:
        """Создает визуальный прогресс-бар"""
        filled = int(length * progress / 100)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}] {progress}%"
    
    # ==================== URL PROCESSING ====================
    
    def _extract_urls_from_message(self, message_text: str) -> List[str]:
        """Извлекает URL из текста сообщения"""
        if not self.url_processor:
            return []
        
        return self.url_processor.extract_urls_from_text(message_text)
    
    async def _process_url_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            url: str, template_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Обрабатывает файл по URL"""
        try:
            # Определяем откуда отправлять сообщения
            if update.message:
                reply_func = update.message.reply_text
                chat_id = update.message.chat_id
            elif update.callback_query:
                reply_func = update.callback_query.message.reply_text
                chat_id = update.callback_query.message.chat_id
            else:
                self.logger.error("❌ Не удалось определить способ отправки сообщения")
                return False, None, None
            
            if not self.url_processor:
                await reply_func("❌ URL обработка недоступна")
                return False, None, None
            
            # Проверяем безопасность URL
            is_safe, reason = self.url_validator.is_safe_url(url)
            if not is_safe:
                await reply_func(f"❌ URL не прошел проверку безопасности: {reason}")
                return False, None, None
            
            # Проверяем поддержку URL
            is_supported, reason = self.url_processor.is_supported_url(url)
            if not is_supported:
                await reply_func(f"❌ URL не поддерживается: {reason}")
                return False, None, None
            
            # Получаем информацию о файле
            await reply_func("🔍 Проверяю файл по ссылке...")
            
            async with self.url_processor as processor:
                file_info = await processor.get_file_info(url)
                
                if not file_info:
                    await reply_func("❌ Не удалось получить информацию о файле")
                    return False, None, None
                
                if not file_info['supported']:
                    await reply_func(f"❌ {file_info['reason']}")
                    return False, None, None
                
                # Показываем информацию о файле (безопасно экранируем)
                file_type_emoji = "🎵" if "audio" in file_info['content_type'] else "🎬"
                cloud_info = f"\n☁️ Сервис: {self._escape_markdown(file_info['cloud_service'].title())}" if file_info['is_cloud'] else ""
                
                # Очищаем имя файла без экранирования (так как не используем backticks)
                filename = self._clean_filename_for_display(file_info['filename'])
                content_type = self._escape_markdown(file_info['content_type'])
                template_escaped = self._escape_markdown(template_name)
                
                info_message = (
                    f"{file_type_emoji} *Файл обнаружен:*\n"
                    f"📎 Имя: {filename}\n"
                    f"📊 Размер: {file_info['size_mb']} МБ\n"
                    f"🎯 Тип: {content_type}{cloud_info}\n"
                    f"📝 Шаблон: {template_escaped}\n\n"
                    f"⏳ Начинаю скачивание и обработку..."
                )
                
                await reply_func(info_message)
                
                # Создаем временную директорию
                temp_dir = tempfile.mkdtemp(prefix="url_download_")
                
                try:
                    # Скачиваем файл
                    await reply_func("📥 Скачиваю файл...")
                    result = await processor.download_file(url, temp_dir)
                    
                    if not result:
                        await reply_func("❌ Ошибка скачивания файла")
                        return False, None, None
                    
                    file_path, updated_file_info = result
                    
                    # Обрабатываем файл
                    success, transcript_file, summary_file = await self._process_with_meeting_processor(
                        update, context, file_path, template_name, chat_id
                    )
                    
                    return success, transcript_file, summary_file
                    
                finally:
                    # Очищаем временную директорию
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception:
                        pass
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки URL {url}: {e}")
            
            # Безопасная отправка сообщения об ошибке (без markdown)
            try:
                error_message = f"❌ Ошибка обработки файла: {str(e)}"
                if update.message:
                    await update.message.reply_text(error_message)
                elif update.callback_query:
                    await update.callback_query.message.reply_text(error_message)
            except Exception:
                self.logger.error("❌ Не удалось отправить сообщение об ошибке")
            
            return False, None, None    
    
    def _clean_filename_for_display(self, filename: str) -> str:
        """Очищает имя файла для корректного отображения"""
        if not filename or filename == 'Неизвестно':
            return filename
        
        # Заменяем обратные слеши на подчеркивания
        filename = filename.replace('\\', '_')
        
        # Заменяем другие проблемные символы
        problematic_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in problematic_chars:
            filename = filename.replace(char, '_')
        
        # Убираем множественные подчеркивания
        while '__' in filename:
            filename = filename.replace('__', '_')
        
        return filename
    
    def _escape_markdown(self, text: str) -> str:
        """Экранирует специальные символы для Markdown"""
        if not text:
            return "Неизвестно"
        
        # Список символов, которые нужно экранировать в Markdown
        # Убираем дефис и подчеркивание из списка для имен файлов
        special_chars = ['*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '=', '|', '{', '}', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    def _escape_markdown_filename(self, text: str) -> str:
        """Специальное экранирование для имен файлов (без дефисов и подчеркиваний)"""
        if not text:
            return "Неизвестно"
        
        # Для имен файлов экранируем только самые критичные символы
        special_chars = ['*', '[', ']', '`']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text

    async def _show_url_file_info(self, update: Update, url: str):
        """Показывает информацию о файле по URL"""
        try:
            # Определяем откуда отправлять сообщение
            if update.message:
                chat_id = update.message.chat_id
                reply_func = update.message.reply_text
            elif update.callback_query:
                chat_id = update.callback_query.message.chat_id
                reply_func = update.callback_query.message.reply_text
            else:
                self.logger.error("❌ Не удалось определить chat_id для отправки сообщения")
                return
            
            if not self.url_processor:
                await reply_func("❌ URL обработка недоступна")
                return
            
            await reply_func("🔍 Получаю информацию о файле...")
            
            async with self.url_processor as processor:
                file_info = await processor.get_file_info(url)
                
                if not file_info:
                    await reply_func("❌ Не удалось получить информацию о файле")
                    return
                
                # Формируем сообщение с информацией (безопасно экранируем)
                file_type_emoji = "🎵" if "audio" in file_info['content_type'] else "🎬"
                status_emoji = "✅" if file_info['supported'] else "❌"
                cloud_info = f"\n☁️ Сервис: {self._escape_markdown(file_info['cloud_service'].title())}" if file_info['is_cloud'] else ""
                
                # Очищаем имя файла без экранирования (так как не используем backticks)
                filename = self._clean_filename_for_display(file_info['filename'] or 'Неизвестно')
                content_type = self._escape_markdown(file_info['content_type'])
                reason = self._escape_markdown(file_info['reason'])
                
                # Обрезаем URL для отображения
                display_url = file_info['original_url'][:50]
                if len(file_info['original_url']) > 50:
                    display_url += "\\.\\.\\."
                display_url = self._escape_markdown(display_url)
                
                info_message = (
                    f"{file_type_emoji} *Информация о файле:*\n\n"
                    f"📎 Имя: {filename}\n"
                    f"📊 Размер: {file_info['size_mb']} МБ\n"
                    f"🎯 Тип: {content_type}\n"
                    f"🔗 URL: {display_url}{cloud_info}\n\n"
                    f"{status_emoji} *Статус:* {reason}"
                )
                
                # Добавляем кнопки для действий
                if file_info['supported']:
                    # Создаем короткий ID для URL
                    short_id = self._create_short_url_id(url)
                    
                    keyboard = [
                        [InlineKeyboardButton("🔄 Обработать файл", callback_data=f"process:{short_id}")],
                        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await reply_func(
                        info_message,
                        reply_markup=reply_markup
                    )
                else:
                    await reply_func(info_message)
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения информации о файле {url}: {e}")
            
            # Безопасная отправка сообщения об ошибке (без markdown)
            try:
                error_message = f"❌ Ошибка: {str(e)}"
                if update.message:
                    await update.message.reply_text(error_message)
                elif update.callback_query:
                    await update.callback_query.message.reply_text(error_message)
            except Exception:
                self.logger.error("❌ Не удалось отправить сообщение об ошибке")
    
    # ==================== FILE PROCESSING ====================
    
    async def _download_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           file_obj, filename: str = None) -> Tuple[Optional[str], Optional[str]]:
        """Скачивает файл во временную директорию"""
        try:
            # Создаем временную директорию
            temp_dir = tempfile.mkdtemp(prefix="meetingbot_")
            
            # Определяем имя файла
            if not filename:
                if hasattr(file_obj, 'file_name') and file_obj.file_name:
                    filename = file_obj.file_name
                else:
                    # Генерируем имя файла
                    file_id = getattr(file_obj, 'file_id', 'unknown')[:8]
                    mime_type = getattr(file_obj, 'mime_type', '')
                    
                    # Сопоставляем MIME типы с расширениями
                    mime_to_ext = {
                        'audio/mpeg': '.mp3', 'audio/mp3': '.mp3', 'audio/wav': '.wav',
                        'audio/flac': '.flac', 'audio/aac': '.aac', 'audio/ogg': '.ogg',
                        'video/mp4': '.mp4', 'video/avi': '.avi', 'video/quicktime': '.mov'
                    }
                    
                    ext = mime_to_ext.get(mime_type.lower(), '.bin')
                    filename = f"file_{file_id}{ext}"
            
            # Безопасное имя файла
            filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            if not filename:
                filename = f"file_{getattr(file_obj, 'file_id', 'unknown')[:8]}.bin"
            
            file_path = Path(temp_dir) / filename
            
            await update.message.reply_text("📥 Скачивание файла...")
            
            # Скачиваем файл
            file = await context.bot.get_file(file_obj.file_id)
            await file.download_to_drive(file_path)
            
            self.logger.info(f"📥 Файл скачан: {file_path}")
            return str(file_path), temp_dir
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка скачивания файла: {e}")
            await update.message.reply_text(f"❌ Ошибка скачивания файла: {str(e)}")
            return None, None
    
    async def _process_with_meeting_processor(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                            file_path: str, template_name: str, chat_id: int = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """Обрабатывает файл с помощью MeetingProcessor"""
        try:
            # Определяем chat_id если не передан
            if chat_id is None:
                if update.message:
                    chat_id = update.message.chat_id
                    reply_func = update.message.reply_text
                elif update.callback_query:
                    chat_id = update.callback_query.message.chat_id
                    reply_func = update.callback_query.message.reply_text
                else:
                    self.logger.error("❌ Не удалось определить chat_id")
                    return False, None, None
            else:
                # Используем bot.send_message для отправки
                reply_func = lambda text, **kwargs: context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
            
            # Проверяем API ключи
            api_keys_valid, error_msg = self._validate_api_keys()
            if not api_keys_valid:
                await reply_func(error_msg)
                return False, None, None
            
            # Создаем выходную директорию
            output_dir = Path(tempfile.mkdtemp(prefix="meeting_output_"))
            
            # Получаем API ключи
            api_keys = self.api_keys.get("api_keys", {})
            
            # Получаем пользовательскую сессию для прогресса
            user_id = update.effective_user.id
            user_session = self.get_user_session(user_id)
            
            # Создаем callback для прогресса
            progress_callback = self._create_progress_callback(user_session, context, chat_id)
            
            # Создаем процессор с callback'ом прогресса
            processor = MeetingProcessor(
                deepgram_api_key=api_keys["deepgram"],
                claude_api_key=api_keys["claude"],
                deepgram_timeout=self.config.get("processing", {}).get("deepgram_timeout", 300),
                claude_model="claude-sonnet-4-20250514",
                chunk_duration_minutes=self.config.get("processing", {}).get("chunk_duration_minutes", 15),
                template_type=template_name,
                deepgram_language=self.config.get("processing", {}).get("language", "ru"),
                deepgram_model=self.config.get("processing", {}).get("deepgram_model", "nova-2"),
                deepgram_proxy=self.config.get("processing", {}).get("deepgram_proxy")
            )
            
            # Устанавливаем callback для прогресса, если поддерживается
            if hasattr(processor, 'set_progress_callback'):
                processor.set_progress_callback(progress_callback.sync)
            else:
                # Если MeetingProcessor не поддерживает progress callback,
                # имитируем базовые этапы прогресса
                await progress_callback(10, "Подготовка к обработке...")
                
                # Запускаем обработку в отдельной задаче для имитации прогресса
                async def simulate_progress():
                    await asyncio.sleep(2)
                    await progress_callback(25, "Начало транскрипции...")
                    await asyncio.sleep(3)
                    await progress_callback(50, "Обработка аудио...")
                    await asyncio.sleep(2)
                    await progress_callback(75, "Генерация протокола...")
                
                # Запускаем имитацию прогресса
                progress_task = asyncio.create_task(simulate_progress())
            
            # Уведомляем о начале обработки
            file_type = FileValidator.get_file_type(file_path)
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            
            # Безопасно экранируем данные для markdown
            template_escaped = self._escape_markdown(template_name)
            
            await reply_func(
                f"🔄 Начинаю обработку...\n"
                f"📁 Тип: {file_type}\n"
                f"📊 Размер: {file_size:.1f} МБ\n"
                f"📝 Шаблон: `{template_escaped}`\n\n"
                f"⏳ Прогресс будет отображаться в реальном времени...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Обрабатываем файл в отдельном потоке, чтобы не блокировать event loop
            import concurrent.futures
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                success = await loop.run_in_executor(
                    executor,
                    processor.process_meeting,
                    file_path,
                    str(output_dir),
                    template_name,
                    False  # keep_audio_file
                )
            
            if not success:
                await progress_callback(0, "Ошибка при обработке файла")
                return False, None, None
            
            # Уведомляем о завершении
            await progress_callback(90, "Обработка завершена, сохранение файлов...")
            
            # Ищем созданные файлы
            input_name = Path(file_path).stem
            transcript_file = output_dir / f"{input_name}_transcript.txt"
            summary_file = output_dir / f"{input_name}_summary.md"
            
            # Проверяем существование файлов
            if not transcript_file.exists() or not summary_file.exists():
                self.logger.error(f"❌ Результирующие файлы не найдены")
                await progress_callback(0, "Результирующие файлы не найдены")
                return False, None, None
            
            # Финальное обновление прогресса
            await progress_callback(100, "Обработка завершена успешно")
            
            self.logger.info(f"✅ Обработка завершена: {transcript_file}, {summary_file}")
            return True, str(transcript_file), str(summary_file)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки: {e}")
            
            # Уведомляем об ошибке через callback прогресса
            try:
                user_id = update.effective_user.id
                user_session = self.get_user_session(user_id)
                if hasattr(user_session, 'status_message_id') and user_session.status_message_id:
                    progress_callback = self._create_progress_callback(user_session, context, chat_id)
                    await progress_callback(0, f"Ошибка: {str(e)}")
            except Exception:
                pass
            
            # Безопасная отправка сообщения об ошибке (без markdown)
            try:
                error_message = f"❌ Ошибка при обработке: {str(e)}"
                if update.message:
                    await update.message.reply_text(error_message)
                elif update.callback_query:
                    await update.callback_query.message.reply_text(error_message)
                else:
                    await context.bot.send_message(chat_id=chat_id, text=error_message)
            except Exception:
                self.logger.error("❌ Не удалось отправить сообщение об ошибке")
            
            return False, None, None

    async def _send_result_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE, transcript_file: str, summary_file: str) -> bool:
        """Отправляет результирующие файлы пользователю"""
        try:
            sent_files = 0
            
            # Определяем chat_id и функцию для отправки сообщений
            if update.message:
                chat_id = update.message.chat_id
                reply_func = update.message.reply_text
            elif update.callback_query:
                chat_id = update.callback_query.message.chat_id
                reply_func = update.callback_query.message.reply_text
            else:
                self.logger.error("❌ Не удалось определить chat_id для отправки файлов")
                return False
            
            # Отправляем транскрипт
            if os.path.exists(transcript_file):
                with open(transcript_file, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=f,
                        filename=os.path.basename(transcript_file),
                        caption="📝 Транскрипт встречи"
                    )
                sent_files += 1
            
            # Отправляем протокол
            if os.path.exists(summary_file):
                with open(summary_file, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=f,
                        filename=os.path.basename(summary_file),
                        caption="📋 Протокол встречи"
                    )
                sent_files += 1
            
            # Уведомление о завершении
            await reply_func(
                f"✅ Обработка завершена!\n"
                f"📎 Отправлено файлов: {sent_files}\n\n"
                f"💡 Используйте /templates для смены шаблона"
            )
            
            return sent_files > 0
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки файлов: {e}")
            
            # Безопасная отправка сообщения об ошибке
            try:
                error_message = f"❌ Ошибка отправки результатов: {str(e)}"
                if update.message:
                    await update.message.reply_text(error_message)
                elif update.callback_query:
                    await update.callback_query.message.reply_text(error_message)
            except Exception:
                self.logger.error("❌ Не удалось отправить сообщение об ошибке")
            
            return False
    
    async def _cleanup_temp_files(self, *temp_dirs):
        """Очищает временные директории"""
        for temp_dir in temp_dirs:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"🗑️ Удалена временная директория: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Не удалось удалить {temp_dir}: {e}")
    
    # ==================== COMMAND HANDLERS ====================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text(
                "❌ У вас нет доступа к этому боту.\n"
                "Обратитесь к администратору."
            )
            return
        
        user_session = self.get_user_session(user_id)
        
        url_info = ""
        if self.url_processor:
            url_info = "\n🔗 Поддержка HTTP ссылок и облачных сервисов"
        
        admin_info = ""
        if self.is_admin(user_id):
            admin_info = "\n🔧 /admin - Панель администратора"
        
        welcome_text = f"""
🎙️ **Добро пожаловать в Meeting Bot!**

Я помогу вам:
📝 Транскрибировать аудио и видео встреч
📋 Создавать структурированные протоколы
🤖 Использовать разные шаблоны протоколов
📊 Отслеживать прогресс обработки в реальном времени{url_info}

**Доступные команды:**
/help - Справка по командам
/templates - Выбрать шаблон протокола
/settings - Настройки обработки
/status - Статус текущих задач
/url \\<ссылка\\> - Обработать файл по ссылке
/check \\<ссылка\\> - Проверить файл без обработки
/formats - Поддерживаемые форматы{admin_info}

**Способы загрузки:**
1️⃣ Прикрепите файл к сообщению (до 20 МБ)
2️⃣ Отправьте HTTP ссылку на файл
3️⃣ Используйте команду /url с ссылкой

🎯 Поддерживаемые форматы:
• Аудио: MP3, WAV, FLAC, AAC, M4A, OGG
• Видео: MP4, AVI, MOV, MKV, WebM

📝 Текущий шаблон: `{user_session.template}`
        """
        
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
        self.logger.info(f"👋 Пользователь {user_id} начал работу с ботом")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        user_id = update.effective_user.id
        max_size = self.config.get("telegram", {}).get("max_file_size_mb", 100)
        max_url_size = self.config.get("url_processing", {}).get("max_file_size_mb", 500)
        timeout = self.config.get("processing", {}).get("processing_timeout", 1800)
        
        url_commands = ""
        if self.url_processor:
            url_commands = """
**Команды для работы с URL:**
/url \\<ссылка\\> - Обработать файл по ссылке
/check \\<ссылка\\> - Проверить файл без обработки
/formats - Поддерживаемые форматы ссылок

**Поддерживаемые сервисы:**
☁️ Google Drive, Яндекс.Диск
🔗 Любые прямые HTTP ссылки
"""
        
        admin_commands = ""
        if self.is_admin(user_id):
            admin_commands = """
**Команды администратора:**
/admin - Панель администратора
/add_user \\<id\\> - Добавить пользователя
/remove_user \\<id\\> - Удалить пользователя
/list_users - Список пользователей
/add_admin \\<id\\> - Добавить администратора
/remove_admin \\<id\\> - Удалить администратора
/list_admins - Список администраторов
/user_info \\<id\\> - Информация о пользователе
/bot_stats - Статистика бота
"""
        
        help_text = f"""
📚 **Справка по использованию бота**

**Основные команды:**
/start - Начать работу с ботом
/help - Показать эту справку
/templates - Выбрать шаблон протокола
/settings - Настройки обработки
/status - Статус обработки файлов
/cancel - Отменить текущую обработку{url_commands}{admin_commands}

**Как использовать:**
1️⃣ Выберите шаблон командой /templates
2️⃣ Отправьте файл или ссылку на файл
3️⃣ Следите за прогрессом в реальном времени
4️⃣ Получите транскрипт и протокол встречи

**Новые возможности:**
📊 Отслеживание прогресса обработки
⏱️ Уведомления о каждом этапе
🔄 Автоматическое обновление статуса

**Доступные шаблоны:**
• `standard` - Универсальный протокол
• `business` - Деловые встречи
• `project` - Проектные встречи
• `standup` - Ежедневные стендапы
• `interview` - Интервью и собеседования
• `brainstorm` - Мозговые штурмы
• `review` - Ретроспективы
• `technical` - Технические обсуждения
• `sales` - Продажи и клиенты

**Ограничения:**
📊 Прямая загрузка: до {max_size} МБ
🔗 Загрузка по ссылке: до {max_url_size} МБ
⏱️ Максимальное время обработки: {timeout//60} минут
🔒 Файлы удаляются после обработки

**Поддержка:**
При проблемах обратитесь к администратору
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def url_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /url <ссылка>"""
        user_id = update.effective_user.id
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        if not self.url_processor:
            await update.message.reply_text(
                "❌ URL обработка недоступна\n"
                "Используйте прямую загрузку файлов"
            )
            return
        
        user_session = self.get_user_session(user_id)
        
        if user_session.processing:
            await update.message.reply_text(
                "⏳ У вас уже обрабатывается файл.\n"
                "Дождитесь завершения или используйте /cancel для отмены."
            )
            return
        
        # Извлекаем URL из команды
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите ссылку на файл\n\n"
                "Использование: `/url https://example.com/file.mp3`\n"
                "Или просто отправьте ссылку в сообщении",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        url = " ".join(context.args)
        
        # Начинаем обработку
        filename = f"url_file_{hash(url) % 10000}"
        user_session.start_processing(filename)
        
        # Запускаем обработку в фоне
        asyncio.create_task(self._process_url_file_task(update, context, url, user_session))
    
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /check <ссылка> - проверка файла без обработки"""
        if not self.url_processor:
            await update.message.reply_text("❌ URL обработка недоступна")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите ссылку на файл\n\n"
                "Использование: `/check https://example.com/file.mp3`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        url = " ".join(context.args)
        await self._show_url_file_info(update, url)
    
    async def formats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /formats - показывает поддерживаемые форматы"""
        url_config = self.config.get("url_processing", {})
        cloud_services = url_config.get("cloud_services", {})
        
        enabled_services = []
        for service, enabled in cloud_services.items():
            if enabled:
                service_names = {
                    'google_drive': 'Google Drive',
                    'yandex_disk': 'Яндекс.Диск'
                }
                enabled_services.append(service_names.get(service, service))
        
        formats_text = f"""
📋 **Поддерживаемые форматы и сервисы**

**🎵 Аудио форматы:**
• MP3, WAV, FLAC, AAC, M4A, OGG, OPUS

**🎬 Видео форматы:**
• MP4, AVI, MOV, MKV, WMV, WebM

**☁️ Облачные сервисы:**
{chr(10).join(f'• {service}' for service in enabled_services) if enabled_services else '• Не настроены'}

**🔗 Прямые ссылки:**
• Любые HTTP/HTTPS ссылки на поддерживаемые файлы

**📏 Ограничения размера:**
• Прямая загрузка: {self.config.get('telegram', {}).get('max_file_size_mb', 20)} МБ
• Загрузка по URL: {url_config.get('max_file_size_mb', 500)} МБ

**💡 Примеры использования:**
```
/url https://drive.google.com/file/d/abc123
/url https://yadi.sk/d/xyz789/meeting.mp3
/check https://example.com/conference.mp4
```
        """
        
        await update.message.reply_text(formats_text, parse_mode=ParseMode.MARKDOWN)
    
    async def templates_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /templates"""
        user_session = self.get_user_session(update.effective_user.id)
        current_template = user_session.template
        
        # Базовые шаблоны
        base_templates = [
            "standard", "business", "project", "standup", "interview",
            "brainstorm", "review", "planning", "technical", "sales"
        ]
        
        # Создаем клавиатуру
        keyboard = []
        
        for template in base_templates:
            status = "✅" if template == current_template else "📋"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {template}",
                    callback_data=f"template_{template}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📝 **Выбор шаблона протокола**

Текущий шаблон: `{current_template}`

Выберите подходящий шаблон для вашей встречи:
        """
        
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def template_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора шаблона и кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("process:"):
            # Обработка URL из кнопки с коротким ID
            short_id = query.data.replace("process:", "")
            url = self._get_url_by_id(short_id)
            
            if not url:
                await query.edit_message_text("❌ Ссылка устарела. Попробуйте еще раз.")
                return
            
            user_session = self.get_user_session(update.effective_user.id)
            
            if user_session.processing:
                await query.edit_message_text(
                    "⏳ У вас уже обрабатывается файл.\n"
                    "Дождитесь завершения или используйте /cancel для отмены."
                )
                return
            
            filename = f"url_file_{hash(url) % 10000}"
            user_session.start_processing(filename)
            
            await query.edit_message_text("🔄 Начинаю обработку файла по ссылке...")
            
            # Запускаем обработку в фоне
            asyncio.create_task(self._process_url_file_task(update, context, url, user_session))
            return
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Операция отменена")
            return
        
        # Обработка выбора шаблона
        if query.data.startswith("template_"):
            template = query.data.replace("template_", "")
            user_session = self.get_user_session(update.effective_user.id)
            user_session.template = template
            
            self.logger.info(f"📝 Пользователь {update.effective_user.id} выбрал шаблон: {template}")
            
            await query.edit_message_text(
                f"✅ Выбран шаблон: `{template}`\n\n"
                "Теперь отправьте файл или ссылку для обработки.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Неизвестный callback
        await query.edit_message_text("❌ Неизвестная команда")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /settings"""
        user_id = update.effective_user.id
        user_session = self.get_user_session(user_id)
        
        # Определяем статус обработки
        if user_session.processing:
            duration = user_session.get_processing_duration()
            progress_info = f" ({user_session.current_progress}%)" if user_session.current_progress > 0 else ""
            processing_status = f"🟢 Обрабатывается{progress_info} ({duration}с)" if duration else f"🟢 Обрабатывается{progress_info}"
        else:
            processing_status = "🔴 Свободен"
        
        url_status = "✅ Включена" if self.url_processor else "❌ Недоступна"
        progress_status = "✅ Включены" if self.config.get("notifications", {}).get("send_progress_updates", True) else "❌ Отключены"
        
        settings_text = f"""
⚙️ **Настройки обработки**

📝 Текущий шаблон: `{user_session.template}`
🔄 Статус: {processing_status}
🔗 URL обработка: {url_status}
📊 Уведомления о прогрессе: {progress_status}
"""
        
        if user_session.current_file:
            settings_text += f"📁 Обрабатывается: `{user_session.current_file}`\n"
            if user_session.current_message:
                settings_text += f"💬 Текущий этап: {user_session.current_message}\n"
        
        settings_text += """
**Доступные действия:**
• /templates - Изменить шаблон
• /cancel - Отменить обработку
• /status - Статус очереди
• /formats - Поддерживаемые форматы
"""
        
        # Администраторская информация
        if self.is_admin(user_id):
            active_sessions = len([s for s in self.user_sessions.values() if s.processing])
            uptime = datetime.now() - self.stats['start_time']
            settings_text += f"""

**📊 Статистика администратора:**
👥 Активных пользователей: {len(self.stats['active_users'])}
⚡ Обрабатывается файлов: {active_sessions}
📈 Всего файлов обработано: {self.stats['total_files_processed']}
🔗 Всего URL обработано: {self.stats['total_urls_processed']}
❌ Всего ошибок: {self.stats['total_errors']}
🕐 Время работы: {uptime.days}д {uptime.seconds//3600}ч {(uptime.seconds//60)%60}м
"""
        
        await update.message.reply_text(
            settings_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        user_id = update.effective_user.id
        user_session = self.get_user_session(user_id)
        
        if user_session.processing:
            duration = user_session.get_processing_duration()
            duration_text = f" ({duration}с)" if duration else ""
            
            # Создаем прогресс-бар
            progress_bar = self._create_progress_bar(user_session.current_progress)
            
            status_text = (
                f"🔄 *Активная обработка:*\n\n"
                f"{progress_bar}\n"
                f"📊 Прогресс: {user_session.current_progress}%\n"
                f"📝 Этап: {user_session.current_message}\n"
                f"📁 Файл: `{user_session.current_file}`\n"
                f"📝 Шаблон: `{user_session.template}`\n"
                f"⏱️ Длительность: {duration_text}\n\n"
                "⏳ Обработка продолжается...\n"
                "Используйте /cancel для отмены."
            )
            
            await update.message.reply_text(
                status_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "🔴 Нет активных задач\n\n"
                "Отправьте файл или ссылку для начала обработки."
            )
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /cancel"""
        user_id = update.effective_user.id
        user_session = self.get_user_session(user_id)
        
        if user_session.processing:
            user_session.stop_processing()
            
            self.logger.info(f"❌ Пользователь {user_id} отменил обработку")
            
            await update.message.reply_text(
                "❌ Обработка отменена\n\n"
                "Отправьте новый файл или ссылку для обработки."
            )
        else:
            await update.message.reply_text(
                "ℹ️ Нет активных задач для отмены"
            )
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /admin - панель администратора"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        admin_text = """
🔧 **Панель администратора**

**Управление пользователями:**
/add\\_user <user\\_id> - Добавить пользователя
/remove\\_user <user\\_id> - Удалить пользователя
/list\\_users - Список разрешенных пользователей
/add\\_admin <user\\_id> - Добавить администратора
/remove\\_admin <user\\_id> - Удалить администратора
/list\\_admins - Список администраторов

**Информация:**
/user\\_info <user\\_id> - Информация о пользователе
/bot\\_stats - Статистика бота

**Примеры:**
`/add_user 123456789`
`/remove_user 123456789`
`/user_info 123456789`
        """
        
        await update.message.reply_text(admin_text, parse_mode=ParseMode.MARKDOWN)
    
    async def add_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /add_user <user_id> - добавить пользователя"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите ID пользователя\n\n"
                "Использование: `/add_user 123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя")
            return
        
        allowed_users = self.config.get("telegram", {}).get("allowed_users", [])
        
        if target_user_id in allowed_users:
            await update.message.reply_text(f"ℹ️ Пользователь {target_user_id} уже имеет доступ")
            return
        
        # Добавляем пользователя
        allowed_users.append(target_user_id)
        self.config["telegram"]["allowed_users"] = allowed_users
        self._save_config(self.config)
        
        self.logger.info(f"👤 Администратор {user_id} добавил пользователя {target_user_id}")
        
        await update.message.reply_text(
            f"✅ Пользователь `{target_user_id}` добавлен в список разрешенных\n\n"
            f"Всего пользователей: {len(allowed_users)}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def remove_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /remove_user <user_id> - удалить пользователя"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите ID пользователя\n\n"
                "Использование: `/remove_user 123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя")
            return
        
        allowed_users = self.config.get("telegram", {}).get("allowed_users", [])
        admin_users = self.config.get("telegram", {}).get("admin_users", [])
        
        if target_user_id not in allowed_users:
            await update.message.reply_text(f"ℹ️ Пользователь {target_user_id} не найден в списке разрешенных")
            return
        
        # Проверяем, не является ли пользователь администратором
        if target_user_id in admin_users:
            await update.message.reply_text(
                f"❌ Нельзя удалить администратора {target_user_id}\n"
                f"Сначала удалите его из администраторов командой `/remove_admin {target_user_id}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Удаляем пользователя
        allowed_users.remove(target_user_id)
        self.config["telegram"]["allowed_users"] = allowed_users
        self._save_config(self.config)
        
        # Останавливаем активную сессию пользователя, если есть
        if target_user_id in self.user_sessions:
            self.user_sessions[target_user_id].stop_processing()
            del self.user_sessions[target_user_id]
        
        self.logger.info(f"👤 Администратор {user_id} удалил пользователя {target_user_id}")
        
        await update.message.reply_text(
            f"✅ Пользователь `{target_user_id}` удален из списка разрешенных\n\n"
            f"Всего пользователей: {len(allowed_users)}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def list_users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /list_users - список разрешенных пользователей"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        allowed_users = self.config.get("telegram", {}).get("allowed_users", [])
        admin_users = self.config.get("telegram", {}).get("admin_users", [])
        
        if not allowed_users:
            await update.message.reply_text("ℹ️ Список разрешенных пользователей пуст")
            return
        
        users_text = "👥 **Разрешенные пользователи:**\n\n"
        
        for i, uid in enumerate(allowed_users, 1):
            status = "👑 Администратор" if uid in admin_users else "👤 Пользователь"
            # Пользователь активен если он в сессиях ИЛИ это текущий пользователь
            active = "🟢 Активен" if (uid in self.user_sessions or uid == user_id) else "⚪ Неактивен"
            users_text += f"{i}. `{uid}` - {status} ({active})\n"
        
        users_text += f"\n**Всего:** {len(allowed_users)} пользователей"
        
        await update.message.reply_text(users_text, parse_mode=ParseMode.MARKDOWN)
    
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /add_admin <user_id> - добавить администратора"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите ID пользователя\n\n"
                "Использование: `/add_admin 123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя")
            return
        
        allowed_users = self.config.get("telegram", {}).get("allowed_users", [])
        admin_users = self.config.get("telegram", {}).get("admin_users", [])
        
        # Проверяем, есть ли пользователь в разрешенных
        if target_user_id not in allowed_users:
            await update.message.reply_text(
                f"❌ Пользователь {target_user_id} не найден в списке разрешенных\n"
                f"Сначала добавьте его командой `/add_user {target_user_id}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if target_user_id in admin_users:
            await update.message.reply_text(f"ℹ️ Пользователь {target_user_id} уже является администратором")
            return
        
        # Добавляем администратора
        admin_users.append(target_user_id)
        self.config["telegram"]["admin_users"] = admin_users
        self._save_config(self.config)
        
        self.logger.info(f"👑 Администратор {user_id} добавил администратора {target_user_id}")
        
        await update.message.reply_text(
            f"✅ Пользователь `{target_user_id}` назначен администратором\n\n"
            f"Всего администраторов: {len(admin_users)}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /remove_admin <user_id> - удалить администратора"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите ID пользователя\n\n"
                "Использование: `/remove_admin 123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя")
            return
        
        admin_users = self.config.get("telegram", {}).get("admin_users", [])
        
        if target_user_id not in admin_users:
            await update.message.reply_text(f"ℹ️ Пользователь {target_user_id} не является администратором")
            return
        
        # Проверяем, не удаляет ли администратор сам себя
        if target_user_id == user_id:
            await update.message.reply_text("❌ Нельзя удалить самого себя из администраторов")
            return
        
        # Проверяем, не остается ли система без администраторов
        if len(admin_users) <= 1:
            await update.message.reply_text("❌ Нельзя удалить последнего администратора")
            return
        
        # Удаляем администратора
        admin_users.remove(target_user_id)
        self.config["telegram"]["admin_users"] = admin_users
        self._save_config(self.config)
        
        self.logger.info(f"👑 Администратор {user_id} удалил администратора {target_user_id}")
        
        await update.message.reply_text(
            f"✅ Пользователь `{target_user_id}` больше не является администратором\n\n"
            f"Всего администраторов: {len(admin_users)}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def list_admins_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /list_admins - список администраторов"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        admin_users = self.config.get("telegram", {}).get("admin_users", [])
        
        if not admin_users:
            await update.message.reply_text("ℹ️ Список администраторов пуст")
            return
        
        admins_text = "👑 **Администраторы:**\n\n"
        
        for i, uid in enumerate(admin_users, 1):
            # Пользователь активен если он в сессиях ИЛИ это текущий пользователь
            active = "🟢 Активен" if (uid in self.user_sessions or uid == user_id) else "⚪ Неактивен"
            current = " (вы)" if uid == user_id else ""
            admins_text += f"{i}. `{uid}` - {active}{current}\n"
        
        admins_text += f"\n**Всего:** {len(admin_users)} администраторов"
        
        await update.message.reply_text(admins_text, parse_mode=ParseMode.MARKDOWN)
    
    async def user_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /user_info <user_id> - информация о пользователе"""
        user_id = update.effective_user.id
        
        # Определяем функцию для отправки сообщений
        if update.message:
            reply_func = update.message.reply_text
        elif update.callback_query:
            reply_func = update.callback_query.message.reply_text
        else:
            # Используем effective_message как fallback
            reply_func = update.effective_message.reply_text if update.effective_message else None
            if not reply_func:
                self.logger.error("❌ Не удалось определить способ отправки сообщения в user_info_command")
                return
        
        if not self.is_admin(user_id):
            await reply_func("❌ У вас нет прав администратора")
            return
        
        if not context.args:
            await reply_func(
                "❌ Укажите ID пользователя\n\n"
                "Использование: `/user_info 123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await reply_func("❌ Неверный формат ID пользователя")
            return
        
        allowed_users = self.config.get("telegram", {}).get("allowed_users", [])
        admin_users = self.config.get("telegram", {}).get("admin_users", [])
        
        # Проверяем доступ
        has_access = len(allowed_users) == 0 or target_user_id in allowed_users
        is_admin = target_user_id in admin_users
        
        # Информация о сессии
        session_info = "⚪ Неактивен"
        if target_user_id in self.user_sessions:
            session = self.user_sessions[target_user_id]
            if session.processing:
                duration = session.get_processing_duration()
                session_info = f"🟡 Обрабатывает файл ({duration}с)" if duration else "🟡 Обрабатывает файл"
            else:
                session_info = "🟢 Активен"
        elif target_user_id == user_id:
            # Если это текущий пользователь, который выполняет команду, он активен
            session_info = "🟢 Активен"
        
        # Статус доступа
        if not has_access:
            access_status = "❌ Нет доступа"
        elif is_admin:
            access_status = "👑 Администратор"
        else:
            access_status = "👤 Пользователь"
        
        info_text = f"""
👤 **Информация о пользователе**

🆔 ID: `{target_user_id}`
🔐 Статус: {access_status}
🔄 Активность: {session_info}
        """
        
        if target_user_id in self.user_sessions:
            session = self.user_sessions[target_user_id]
            info_text += f"\n📝 Шаблон: `{session.template}`"
            if session.current_file:
                info_text += f"\n📁 Файл: `{session.current_file}`"
                info_text += f"\n📊 Прогресс: {session.current_progress}%"
        
        await reply_func(info_text, parse_mode=ParseMode.MARKDOWN)
    
    async def bot_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /bot_stats - статистика бота"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        allowed_users = self.config.get("telegram", {}).get("allowed_users", [])
        admin_users = self.config.get("telegram", {}).get("admin_users", [])
        active_sessions = len([s for s in self.user_sessions.values() if s.processing])
        uptime = datetime.now() - self.stats['start_time']
        
        stats_text = f"""
📊 **Статистика бота**

👥 **Пользователи:**
• Всего разрешенных: {len(allowed_users)}
• Администраторов: {len(admin_users)}
• Активных сессий: {len(self.user_sessions)}
• Обрабатывается файлов: {active_sessions}

📈 **Обработка:**
• Всего файлов: {self.stats['total_files_processed']}
• Всего URL: {self.stats['total_urls_processed']}
• Всего ошибок: {self.stats['total_errors']}

⚙️ **Система:**
• Время работы: {uptime.days}д {uptime.seconds//3600}ч {(uptime.seconds//60)%60}м
• URL обработка: {'✅ Включена' if self.url_processor else '❌ Отключена'}
• Уведомления: {'✅ Включены' if self.config.get('notifications', {}).get('send_progress_updates', True) else '❌ Отключены'}

🔧 **Конфигурация:**
• Макс. размер файла: {self.config.get('telegram', {}).get('max_file_size_mb', 20)} МБ
• Макс. размер URL: {self.config.get('url_processing', {}).get('max_file_size_mb', 500)} МБ
• Таймаут обработки: {self.config.get('processing', {}).get('processing_timeout', 1800)//60} мин
        """
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    
    # ==================== FILE HANDLERS ====================
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженных файлов"""
        user_id = update.effective_user.id
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        user_session = self.get_user_session(user_id)
        
        if user_session.processing:
            await update.message.reply_text(
                "⏳ У вас уже обрабатывается файл.\n"
                "Дождитесь завершения или используйте /cancel для отмены."
            )
            return
        
        document = update.message.document
        max_size_mb = self.config.get("telegram", {}).get("max_file_size_mb", 100)
        
        # Валидируем файл
        is_valid, error_msg = FileValidator.validate_file(document, max_size_mb)
        if not is_valid:
            await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Начинаем обработку
        filename = document.file_name or f"document_{document.file_id[:8]}"
        user_session.start_processing(filename)
        
        # Запускаем обработку в фоне
        asyncio.create_task(self._process_file(update, context, document))
    
    async def handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка аудио сообщений"""
        user_id = update.effective_user.id
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        user_session = self.get_user_session(user_id)
        
        if user_session.processing:
            await update.message.reply_text(
                "⏳ У вас уже обрабатывается файл.\n"
                "Дождитесь завершения или используйте /cancel для отмены."
            )
            return
        
        audio = update.message.audio
        max_size_mb = self.config.get("telegram", {}).get("max_file_size_mb", 100)
        
        # Валидируем файл
        is_valid, error_msg = FileValidator.validate_file(audio, max_size_mb)
        if not is_valid:
            await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Начинаем обработку
        filename = audio.file_name or f"audio_{audio.file_id[:8]}.mp3"
        user_session.start_processing(filename)
        
        # Используем общую логику обработки
        asyncio.create_task(self._process_file(update, context, audio))
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосовых сообщений"""
        user_id = update.effective_user.id
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        user_session = self.get_user_session(user_id)
        
        if user_session.processing:
            await update.message.reply_text(
                "⏳ У вас уже обрабатывается файл.\n"
                "Дождитесь завершения или используйте /cancel для отмены."
            )
            return
        
        voice = update.message.voice
        max_size_mb = self.config.get("telegram", {}).get("max_file_size_mb", 100)
        
        # Валидируем файл
        is_valid, error_msg = FileValidator.validate_file(voice, max_size_mb)
        if not is_valid:
            await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Начинаем обработку
        filename = f"voice_{voice.file_id[:8]}.ogg"
        user_session.start_processing(filename)
        
        # Используем общую логику обработки
        asyncio.create_task(self._process_file(update, context, voice))
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка видео сообщений"""
        user_id = update.effective_user.id
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        user_session = self.get_user_session(user_id)
        
        if user_session.processing:
            await update.message.reply_text(
                "⏳ У вас уже обрабатывается файл.\n"
                "Дождитесь завершения или используйте /cancel для отмены."
            )
            return
        
        video = update.message.video
        max_size_mb = self.config.get("telegram", {}).get("max_file_size_mb", 100)
        
        # Валидируем файл
        is_valid, error_msg = FileValidator.validate_file(video, max_size_mb)
        if not is_valid:
            await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Начинаем обработку
        filename = video.file_name or f"video_{video.file_id[:8]}.mp4"
        user_session.start_processing(filename)
        
        # Используем общую логику обработки
        asyncio.create_task(self._process_file(update, context, video))
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_id = update.effective_user.id
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        message_text = update.message.text
        
        # Проверяем наличие URL в сообщении
        if self.url_processor and self.config.get("url_processing", {}).get("auto_detect_links", True):
            urls = self._extract_urls_from_message(message_text)
            
            if urls:
                # Обрабатываем первый найденный URL
                url = urls[0]
                
                user_session = self.get_user_session(user_id)
                
                if user_session.processing:
                    await update.message.reply_text(
                        "⏳ У вас уже обрабатывается файл.\n"
                        "Дождитесь завершения или используйте /cancel для отмены."
                    )
                    return
                
                # Показываем информацию о найденном файле с кнопками
                await self._show_url_file_info(update, url)
                return
        
        # Обычное сообщение без URL
        help_msg = "🤖 Отправьте файл или ссылку для обработки.\n\n"
        help_msg += "Используйте:\n"
        help_msg += "• /help - для справки\n"
        help_msg += "• /templates - для выбора шаблона\n"
        help_msg += "• /settings - для настроек\n"
        help_msg += "• /status - для просмотра прогресса\n"
        
        if self.url_processor:
            help_msg += "• /url \\<ссылка\\> - для обработки файла по ссылке"
        
        await update.message.reply_text(help_msg)
    
    # ==================== CORE PROCESSING ====================
    
    async def _process_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_obj):
        """Основная логика обработки файлов"""
        user_id = update.effective_user.id
        user_session = self.get_user_session(user_id)
        temp_dirs = []
        
        try:
            # Скачиваем файл
            file_path, temp_dir = await self._download_file(update, context, file_obj)
            if not file_path:
                return
            
            temp_dirs.append(temp_dir)
            
            # Обрабатываем файл
            success, transcript_file, summary_file = await self._process_with_meeting_processor(
                update, context, file_path, user_session.template
            )
            
            if success and transcript_file and summary_file:
                # Отправляем результаты
                await self._send_result_files(update, context, transcript_file, summary_file)
                self.stats['total_files_processed'] += 1
                
                # Добавляем папку с результатами к временным папкам для очистки
                temp_dirs.append(str(Path(transcript_file).parent))
            
        except Exception as e:
            await self._handle_processing_error(update, e, user_session)
        finally:
            user_session.stop_processing()
            await self._cleanup_temp_files(*temp_dirs)
    
    async def _process_url_file_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   url: str, user_session: UserSession):
        """Задача обработки файла по URL"""
        temp_dirs = []
        
        try:
            # Обрабатываем файл по URL
            success, transcript_file, summary_file = await self._process_url_file(
                update, context, url, user_session.template
            )
            
            if success and transcript_file and summary_file:
                # Отправляем результаты
                await self._send_result_files(update, context, transcript_file, summary_file)
                self.stats['total_urls_processed'] += 1
                
                # Добавляем папку с результатами к временным папкам для очистки
                temp_dirs.append(str(Path(transcript_file).parent))
            
        except Exception as e:
            await self._handle_processing_error(update, e, user_session, "URL файла")
        finally:
            user_session.stop_processing()
            await self._cleanup_temp_files(*temp_dirs)
    
    async def _handle_processing_error(self, update: Update, error: Exception, 
                                     user_session: UserSession, file_type: str = "файла"):
        """Обрабатывает ошибки при обработке файлов"""
        self.stats['total_errors'] += 1
        user_session.stop_processing()
        
        error_msg = str(error)
        self.logger.error(f"❌ Ошибка обработки {file_type} пользователя {update.effective_user.id}: {error_msg}")
        
        # Безопасная отправка сообщения об ошибке
        try:
            if update.message:
                await update.message.reply_text(
                    f"❌ Произошла ошибка при обработке {file_type}\n\n"
                    f"Попробуйте:\n"
                    f"• Проверить формат файла\n"
                    f"• Уменьшить размер файла\n"
                    f"• Попробовать позже\n\n"
                    f"Если проблема повторяется, обратитесь к администратору."
                )
            elif update.callback_query:
                await update.callback_query.message.reply_text(
                    f"❌ Произошла ошибка при обработке {file_type}\n\n"
                    f"Попробуйте:\n"
                    f"• Проверить формат файла\n"
                    f"• Уменьшить размер файла\n"
                    f"• Попробовать позже\n\n"
                    f"Если проблема повторяется, обратитесь к администратору."
                )
        except Exception:
            self.logger.error("❌ Не удалось отправить сообщение об ошибке")
    
    # ==================== ERROR HANDLERS ====================
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        self.logger.error(f"Exception while handling an update: {context.error}")
        self.logger.error(traceback.format_exc())
        
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Произошла внутренняя ошибка.\n"
                    "Попробуйте еще раз или обратитесь к администратору."
                )
            except Exception:
                pass  # Игнорируем ошибки при отправке сообщения об ошибке
    
    # ==================== BOT RUNNER ====================
    
    def run(self):
        """Запуск бота"""
        # Проверяем токен
        bot_token = self.api_keys.get("api_keys", {}).get("telegram_bot_token", "")
        
        if not bot_token:
            self.logger.error("❌ Токен бота не настроен")
            print("❌ Токен бота не настроен!")
            print("Установите переменную окружения TELEGRAM_BOT_TOKEN")
            return
        
        # Проверяем API ключи
        api_keys_valid, error_msg = self._validate_api_keys()
        if not api_keys_valid:
            self.logger.error(error_msg)
            print(error_msg)
            print("Настройте API ключи в переменных окружения (DEEPGRAM_API_KEY, CLAUDE_API_KEY)")
            return
        
        # Создаем приложение
        application = Application.builder().token(bot_token).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("templates", self.templates_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("cancel", self.cancel_command))

        # Админские команды
        application.add_handler(CommandHandler("admin", self.admin_command))
        application.add_handler(CommandHandler("add_user", self.add_user_command))
        application.add_handler(CommandHandler("remove_user", self.remove_user_command))
        application.add_handler(CommandHandler("list_users", self.list_users_command))
        application.add_handler(CommandHandler("add_admin", self.add_admin_command))
        application.add_handler(CommandHandler("remove_admin", self.remove_admin_command))
        application.add_handler(CommandHandler("list_admins", self.list_admins_command))
        application.add_handler(CommandHandler("user_info", self.user_info_command))
        application.add_handler(CommandHandler("bot_stats", self.bot_stats_command))

        # URL команды (если доступны)
        if self.url_processor:
            application.add_handler(CommandHandler("url", self.url_command))
            application.add_handler(CommandHandler("check", self.check_command))
            application.add_handler(CommandHandler("formats", self.formats_command))
        
        # Обработчик callback'ов
        application.add_handler(CallbackQueryHandler(self.template_callback))
        
        # Обработчики файлов
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        application.add_handler(MessageHandler(filters.AUDIO, self.handle_audio))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        application.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Обработчик ошибок
        application.add_error_handler(self.error_handler)
        
        self.logger.info("🚀 Telegram бот запущен")
        print("🤖 Meeting Bot запущен!")
        print("📱 Отправьте /start боту для начала работы")
        print("📊 Отслеживание прогресса в реальном времени включено")
        
        if self.url_processor:
            print("🔗 Поддержка URL обработки включена")
            print("☁️ Облачные сервисы: Google Drive, Яндекс.Диск")
        else:
            print("⚠️ URL обработка недоступна")
        
        print("📊 Логи записываются в logs/telegram_bot.log")
        print("🔧 Конфигурация: bot_config.json")
        
        # Запускаем бота
        try:
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            self.logger.info("👋 Бот остановлен пользователем")
            print("\n👋 Бот остановлен")
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка при запуске: {e}")
            print(f"❌ Критическая ошибка: {e}")

def main():
    """Основная функция"""
    try:
        # Проверяем наличие основных файлов
        required_files = ["meeting_processor.py"]
        missing_files = [f for f in required_files if not os.path.exists(f)]
        
        if missing_files:
            print("❌ Отсутствуют необходимые файлы:")
            for file in missing_files:
                print(f"   - {file}")
            print("\nУбедитесь, что все файлы находятся в одной папке с telegram_bot.py")
            return
        
        # Создаем необходимые директории
        os.makedirs("logs", exist_ok=True)
        os.makedirs("temp_bot_files", exist_ok=True)
        os.makedirs("meeting_output", exist_ok=True)
        
        # Запускаем бота
        bot = MeetingBot()
        bot.run()
        
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        print("Проверьте логи для получения подробной информации")

if __name__ == "__main__":
    main()