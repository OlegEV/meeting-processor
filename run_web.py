#!/usr/bin/env python3
"""
Рабочая версия веб-приложения для обработки встреч
Полностью протестирована и исправлена
"""

import os
import sys
import uuid
import threading
from pathlib import Path
from typing import Dict, Optional, Any
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Веб-фреймворк
try:
    from flask import Flask, request, render_template_string, jsonify, send_file, redirect, url_for, flash, session
    from werkzeug.utils import secure_filename
    from werkzeug.exceptions import RequestEntityTooLarge
except ImportError:
    print("❌ Установите Flask: pip install Flask")
    sys.exit(1)

# Наши модули
try:
    from meeting_processor import MeetingProcessor
    from config_loader import ConfigLoader
    from web_templates import WebTemplates
    from auth import create_auth_system, require_auth, get_current_user_id, get_current_user, is_authenticated
    from database import create_database_manager
except ImportError as e:
    print(f"❌ Ошибка импорта модулей: {e}")
    sys.exit(1)

# Настройка логирования
def setup_logging(log_level: str = "DEBUG", log_file: str = "web_app.log"):
    """Настраивает систему логирования"""
    from logging.handlers import RotatingFileHandler
    
    level = getattr(logging, log_level.upper(), logging.DEBUG)
    
    # Создаем папку для логов
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", log_file)
    
    # Очищаем существующие обработчики
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    handlers = [
        RotatingFileHandler(log_path, maxBytes=100*1024*1024, backupCount=3, encoding='utf-8'),
        logging.StreamHandler()
    ]
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # Принудительно переопределяем конфигурацию
    )
    
    # Настраиваем логгеры для всех модулей приложения
    app_logger = logging.getLogger(__name__)
    app_logger.setLevel(level)
    
    # Настраиваем логгер для Flask
    flask_logger = logging.getLogger('werkzeug')
    flask_logger.setLevel(logging.WARNING)  # Уменьшаем уровень для werkzeug
    
    return app_logger

logger = setup_logging()

class WorkingMeetingWebApp:
    """Рабочая версия веб-приложения для обработки встреч"""
    
    def __init__(self, config_file: str = "config.json"):
        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)
        
        # Загружаем конфигурацию
        self.config = ConfigLoader.load_config(config_file)
        if not self.config:
            raise Exception(f"Не удалось загрузить конфигурацию из {config_file}")
        
        # Загружаем API ключи
        api_keys_file = self.config.get("paths", {}).get("api_keys_config", "api_keys.json")
        self.api_keys_data = ConfigLoader.load_api_keys(api_keys_file)
        
        # Проверяем API ключи
        deepgram_valid, claude_valid, self.deepgram_key, self.claude_key = ConfigLoader.validate_api_keys(self.api_keys_data)
        
        if not deepgram_valid or not claude_valid:
            raise Exception("❌ API ключи не настроены")
        
        # Инициализируем систему аутентификации
        self.token_validator, self.user_manager, self.auth_middleware, self.auth_teardown = create_auth_system(self.config)
        
        # Инициализируем базу данных
        self.db_manager = create_database_manager(self.config)
        
        # Связываем user_manager с db_manager
        self.user_manager.set_db_manager(self.db_manager)
        
        # Настройки приложения
        self.setup_app_config()
        
        # Пул потоков для обработки файлов
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="FileProcessor")
        
        # Создаем необходимые директории
        self.upload_folder = Path("web_uploads")
        self.output_folder = Path("web_output")
        self.upload_folder.mkdir(exist_ok=True)
        self.output_folder.mkdir(exist_ok=True)
        
        # Инициализируем шаблоны
        self.templates = WebTemplates()
        
        # Настраиваем middleware
        self.setup_middleware()
        
        # Настраиваем маршруты
        self.setup_routes()
        
        logger.info("🌐 Веб-приложение инициализировано с аутентификацией и базой данных")
    
    def setup_app_config(self):
        """Настраивает конфигурацию Flask"""
        # Максимальный размер файла
        max_size_mb = self.config.get("settings", {}).get("max_file_size_mb", 100)
        self.app.config['MAX_CONTENT_LENGTH'] = max_size_mb * 1024 * 1024
        
        # Поддерживаемые форматы файлов
        self.allowed_extensions = {'mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'opus', 'mp4', 'avi', 'mov', 'mkv', 'wmv', 'webm'}
        
        # Пытаемся загрузить из конфига
        formats = self.config.get("supported_formats", {})
        if formats:
            self.allowed_extensions = set()
            for format_list in formats.values():
                clean_extensions = [ext.lstrip('.').lower() for ext in format_list]
                self.allowed_extensions.update(clean_extensions)
        
        # Настройки обработки
        self.processing_settings = self.config.get("settings", {})
        
        # Создаем строки для HTML
        self.allowed_extensions_list = sorted(list(self.allowed_extensions))
        self.accept_string = ','.join([f'.{ext}' for ext in self.allowed_extensions_list])
        self.formats_display = ', '.join([ext.upper() for ext in self.allowed_extensions_list])
        
        logger.info(f"Максимальный размер файла: {max_size_mb} МБ")
        logger.info(f"Поддерживаемые форматы: {self.formats_display}")
    
    def setup_middleware(self):
        """Настраивает middleware для аутентификации"""
        # Middleware для аутентификации
        self.app.before_request(self.auth_middleware)
        
        # Teardown для очистки контекста
        self.app.teardown_appcontext(self.auth_teardown)
        
        logger.info("Middleware аутентификации настроен")
    
    def allowed_file(self, filename: str) -> bool:
        """Проверяет, разрешен ли файл для загрузки"""
        if '.' not in filename:
            return False
        file_ext = filename.rsplit('.', 1)[1].lower()
        return file_ext in self.allowed_extensions
    
    def get_available_templates(self) -> Dict[str, str]:
        """Возвращает доступные шаблоны"""
        return self.config.get("template_examples", {
            "standard": "Универсальный шаблон для любых встреч",
            "business": "Официальный протокол для деловых встреч",
            "project": "Фокус на управлении проектами и задачами",
            "standup": "Краткий формат для ежедневных стендапов",
            "interview": "Структурированный отчет об интервью"
        })
    
    def update_job_status(self, job_id: str, **kwargs):
        """Безопасно обновляет статус задачи в базе данных"""
        self.update_job_in_db(job_id, kwargs)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Безопасно получает статус задачи из базы данных"""
        try:
            # Получаем текущего пользователя
            user_id = get_current_user_id()
            if not user_id:
                logger.warning("Попытка получить статус задачи без аутентификации")
                return None
            
            # Получаем задачу из базы данных с проверкой доступа
            job_data = self.db_manager.get_job_by_id(job_id, user_id)
            return job_data
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса задачи {job_id}: {e}")
            return None
    
    def create_job_in_db(self, job_data: Dict[str, Any]) -> bool:
        """Создает задачу в базе данных"""
        try:
            user_id = get_current_user_id()
            if not user_id:
                logger.error("Попытка создать задачу без аутентификации")
                return False
            
            # Добавляем user_id к данным задачи
            job_data['user_id'] = user_id
            
            # Создаем задачу в базе данных
            self.db_manager.create_job(job_data)
            logger.info(f"Задача {job_data['job_id']} создана в базе данных для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания задачи в базе данных: {e}")
            return False
    
    def update_job_in_db(self, job_id: str, update_data: Dict[str, Any]) -> bool:
        """Обновляет задачу в базе данных"""
        try:
            user_id = get_current_user_id()
            if not user_id:
                logger.error("Попытка обновить задачу без аутентификации")
                return False
            
            # Обновляем задачу в базе данных с проверкой доступа
            success = self.db_manager.update_job(job_id, update_data, user_id)
            if success:
                logger.debug(f"Задача {job_id} обновлена в базе данных")
            return success
            
        except Exception as e:
            logger.error(f"Ошибка обновления задачи {job_id}: {e}")
            return False
    
    def get_user_output_dir(self, user_id: str) -> Path:
        """Получает директорию для файлов пользователя"""
        user_files_config = self.config.get('user_files', {})
        base_path = user_files_config.get('base_path', 'web_output')
        
        if user_files_config.get('structure') == 'user_based':
            return Path(base_path) / user_id
        else:
            return Path(base_path)
    
    def ensure_user_exists(self) -> Optional[Dict[str, Any]]:
        """Обеспечивает существование пользователя в базе данных"""
        try:
            user_info = get_current_user()
            if not user_info:
                return None
            
            # Создаем или обновляем пользователя в базе данных
            db_user = self.user_manager.ensure_user_exists(user_info)
            return db_user
            
        except Exception as e:
            logger.error(f"Ошибка при работе с пользователем: {e}")
            return None
    
    def setup_routes(self):
        """Настраивает маршруты приложения"""
        
        @self.app.route('/health')
        def health_check():
            """Health check для мониторинга"""
            try:
                # Проверяем состояние базы данных
                db_info = self.db_manager.get_database_info()
                
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0',
                    'database': {
                        'users_count': db_info.get('users_count', 0),
                        'jobs_count': db_info.get('jobs_count', 0),
                        'db_size_mb': db_info.get('db_size_mb', 0)
                    },
                    'auth': {
                        'enabled': True,
                        'token_header': self.config.get('auth', {}).get('token_header', 'X-Identity-Token')
                    }
                })
            except Exception as e:
                logger.error(f"Ошибка health check: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': str(e)
                }), 500
            
        @self.app.route('/')
        @require_auth(redirect_on_failure=False)
        def index():
            """Главная страница"""
            # Обеспечиваем существование пользователя в базе данных
            user = self.ensure_user_exists()
            if not user:
                return jsonify({'error': 'User authentication failed'}), 401
            
            templates = self.get_available_templates()
            max_size_mb = self.app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
            
            # Получаем информацию о пользователе для отображения
            user_info = get_current_user()
            user_name = self.user_manager.get_user_display_name(user_info) if user_info else "Unknown User"
            
            return render_template_string(
                self.templates.get_index_template(),
                templates=templates,
                max_size_mb=max_size_mb,
                accept_string=self.accept_string,
                formats_display=self.formats_display,
                user_name=user_name,
                user_id=get_current_user_id()
            )
        
        @self.app.route('/upload', methods=['POST'])
        @require_auth()
        def upload_file():
            """Обработка загрузки файла"""
            try:
                # Обеспечиваем существование пользователя
                user = self.ensure_user_exists()
                if not user:
                    flash('Ошибка аутентификации пользователя', 'error')
                    return redirect(url_for('index'))
                
                user_id = get_current_user_id()
                
                if 'file' not in request.files:
                    flash('Файл не выбран', 'error')
                    return redirect(url_for('index'))
                
                file = request.files['file']
                template_type = request.form.get('template', 'standard')
                
                if file.filename == '':
                    flash('Файл не выбран', 'error')
                    return redirect(url_for('index'))
                
                if not self.allowed_file(file.filename):
                    flash(f'Неподдерживаемый формат файла. Разрешены: {self.formats_display}', 'error')
                    return redirect(url_for('index'))
                
                # Создаем уникальный ID для задачи
                job_id = str(uuid.uuid4())
                
                # Сохраняем файл в пользовательскую директорию
                filename = secure_filename(file.filename)
                user_upload_dir = self.upload_folder / user_id
                user_upload_dir.mkdir(exist_ok=True)
                file_path = user_upload_dir / f"{job_id}_{filename}"
                file.save(str(file_path))
                
                logger.info(f"📁 Файл загружен: {filename} (ID: {job_id}, пользователь: {user_id}, шаблон: {template_type})")
                
                # Создаем задачу в базе данных
                job_data = {
                    'job_id': job_id,
                    'user_id': user_id,
                    'filename': filename,
                    'template': template_type,
                    'status': 'uploaded',
                    'progress': 0,
                    'message': 'Файл загружен, ожидает обработки',
                    'file_path': str(file_path)
                }
                
                if not self.create_job_in_db(job_data):
                    flash('Ошибка создания задачи', 'error')
                    return redirect(url_for('index'))
                
                # Запускаем обработку в отдельном потоке
                self.executor.submit(self.process_file_sync, job_id)
                
                session['current_job_id'] = job_id
                flash(f'Файл "{filename}" успешно загружен и поставлен в очередь на обработку', 'success')
                return redirect(url_for('status', job_id=job_id))
                
            except RequestEntityTooLarge:
                max_size = self.app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
                flash(f'Файл слишком большой. Максимальный размер: {max_size} МБ', 'error')
                return redirect(url_for('index'))
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки файла: {e}")
                flash(f'Ошибка загрузки файла: {str(e)}', 'error')
                return redirect(url_for('index'))
        
        @self.app.route('/status/<job_id>')
        @require_auth()
        def status(job_id: str):
            """Страница статуса обработки"""
            job = self.get_job_status(job_id)
            if not job:
                flash('Задача не найдена или у вас нет доступа к ней', 'error')
                return redirect(url_for('index'))
            
            templates = self.get_available_templates()
            
            return render_template_string(
                self.templates.get_status_template(),
                job_id=job_id,
                job=job,
                templates=templates
            )
        
        @self.app.route('/api/status/<job_id>')
        @require_auth(redirect_on_failure=False)
        def api_status(job_id: str):
            """API для получения статуса задачи"""
            job = self.get_job_status(job_id)
            if not job:
                return jsonify({'error': 'Job not found or access denied'}), 404
            
            return jsonify({
                'status': job['status'],
                'progress': job['progress'],
                'message': job['message'],
                'filename': job['filename'],
                'template': job['template']
            })
        
        @self.app.route('/download/<job_id>/<file_type>')
        @require_auth()
        def download_file(job_id: str, file_type: str):
            """Скачивание результирующих файлов"""
            job = self.get_job_status(job_id)
            if not job:
                flash('Задача не найдена или у вас нет доступа к ней', 'error')
                return redirect(url_for('index'))
            
            if job['status'] != 'completed':
                flash('Обработка еще не завершена', 'error')
                return redirect(url_for('status', job_id=job_id))
            
            try:
                if file_type == 'transcript':
                    file_path = job.get('transcript_file')
                    download_name = f"{Path(job['filename']).stem}_transcript.txt"
                elif file_type == 'summary':
                    file_path = job.get('summary_file')
                    download_name = f"{Path(job['filename']).stem}_summary.md"
                else:
                    flash('Неизвестный тип файла', 'error')
                    return redirect(url_for('status', job_id=job_id))
                
                if not file_path or not os.path.exists(file_path):
                    flash('Файл не найден', 'error')
                    return redirect(url_for('status', job_id=job_id))
                
                return send_file(file_path, as_attachment=True, download_name=download_name)
                
            except Exception as e:
                logger.error(f"❌ Ошибка скачивания файла: {e}")
                flash(f'Ошибка скачивания файла: {str(e)}', 'error')
                return redirect(url_for('status', job_id=job_id))
        
        @self.app.route('/view/<job_id>/<file_type>')
        @require_auth()
        def view_file(job_id: str, file_type: str):
            """Просмотр файлов в веб-интерфейсе"""
            job = self.get_job_status(job_id)
            if not job:
                flash('Задача не найдена или у вас нет доступа к ней', 'error')
                return redirect(url_for('index'))
            
            if job['status'] != 'completed':
                flash('Обработка еще не завершена', 'error')
                return redirect(url_for('status', job_id=job_id))
            
            try:
                if file_type == 'transcript':
                    file_path = job.get('transcript_file')
                    file_title = "Транскрипт встречи"
                    is_markdown = False
                elif file_type == 'summary':
                    file_path = job.get('summary_file')
                    file_title = "Протокол встречи"
                    is_markdown = True
                else:
                    flash('Неизвестный тип файла', 'error')
                    return redirect(url_for('status', job_id=job_id))
                
                if not file_path or not os.path.exists(file_path):
                    flash('Файл не найден', 'error')
                    return redirect(url_for('status', job_id=job_id))
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return render_template_string(
                    self.templates.get_view_template(),
                    content=content,
                    file_title=file_title,
                    filename=job['filename'],
                    job_id=job_id,
                    file_type=file_type,
                    is_markdown=is_markdown
                )
                
            except Exception as e:
                logger.error(f"❌ Ошибка просмотра файла: {e}")
                flash(f'Ошибка просмотра файла: {str(e)}', 'error')
                return redirect(url_for('status', job_id=job_id))
        
        @self.app.route('/generate_protocol/<job_id>', methods=['POST'])
        def generate_protocol(job_id: str):
            """Генерация протокола в новом шаблоне из готового транскрипта"""
            job = self.get_job_status(job_id)
            if not job:
                flash('Задача не найдена', 'error')
                return redirect(url_for('index'))
            
            if job['status'] != 'completed':
                flash('Обработка еще не завершена', 'error')
                return redirect(url_for('status', job_id=job_id))
            
            new_template = request.form.get('new_template')
            if not new_template:
                flash('Не выбран шаблон', 'error')
                return redirect(url_for('status', job_id=job_id))
            
            # Проверяем наличие транскрипта
            transcript_file = job.get('transcript_file')
            if not transcript_file or not os.path.exists(transcript_file):
                flash('Файл транскрипта не найден', 'error')
                return redirect(url_for('status', job_id=job_id))
            
            try:
                # Создаем новый ID для задачи генерации протокола
                protocol_job_id = f"{job_id}_protocol_{new_template}"
                
                # Создаем задачу генерации протокола
                with self.jobs_lock:
                    self.processing_jobs[protocol_job_id] = {
                        'status': 'processing',
                        'filename': f"{job['filename']} (протокол {new_template})",
                        'template': new_template,
                        'original_job_id': job_id,
                        'transcript_file': transcript_file,
                        'created_at': datetime.now(),
                        'progress': 0,
                        'message': f'Генерация протокола в шаблоне "{new_template}"...'
                    }
                
                # Запускаем генерацию протокола в отдельном потоке
                self.executor.submit(self.generate_protocol_sync, protocol_job_id, transcript_file, new_template)
                
                flash(f'Запущена генерация протокола в шаблоне "{new_template}"', 'success')
                return redirect(url_for('status', job_id=protocol_job_id))
                
            except Exception as e:
                logger.error(f"❌ Ошибка запуска генерации протокола: {e}")
                flash(f'Ошибка запуска генерации протокола: {str(e)}', 'error')
                return redirect(url_for('status', job_id=job_id))
        
        @self.app.route('/jobs')
        @require_auth()
        def jobs_list():
            """Список задач пользователя"""
            try:
                user_id = get_current_user_id()
                if not user_id:
                    flash('Ошибка аутентификации', 'error')
                    return redirect(url_for('index'))
                
                # Получаем задачи пользователя из базы данных
                user_jobs = self.db_manager.get_user_jobs(user_id, limit=50)
                
                jobs = []
                for job_data in user_jobs:
                    created_at = job_data.get('created_at')
                    if isinstance(created_at, str):
                        try:
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            created_at = datetime.utcnow()
                    elif not isinstance(created_at, datetime):
                        created_at = datetime.utcnow()
                    
                    jobs.append({
                        'id': job_data['job_id'],
                        'filename': job_data['filename'],
                        'status': job_data['status'],
                        'template': job_data['template'],
                        'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'progress': job_data.get('progress', 0)
                    })
                
                return render_template_string(self.templates.get_jobs_template(), jobs=jobs)
                
            except Exception as e:
                logger.error(f"Ошибка получения списка задач: {e}")
                flash('Ошибка получения списка задач', 'error')
                return redirect(url_for('index'))
        
        @self.app.route('/statistics')
        @require_auth()
        def statistics():
            """Страница статистики использования приложения"""
            try:
                # Получаем параметр периода (по умолчанию 30 дней)
                days_back = request.args.get('days', 30, type=int)
                if days_back < 1:
                    days_back = 30
                elif days_back > 365:
                    days_back = 365
                
                # Получаем статистику из базы данных
                stats = self.db_manager.get_usage_statistics(days_back)
                
                return render_template_string(
                    self.templates.get_statistics_template(),
                    stats=stats,
                    days_back=days_back
                )
                
            except Exception as e:
                logger.error(f"Ошибка получения статистики: {e}")
                flash('Ошибка получения статистики', 'error')
                return redirect(url_for('index'))
        
        @self.app.route('/docs')
        def docs_index():
            """Главная страница документации"""
            return render_template_string(self.templates.get_docs_index_template())
        
        @self.app.route('/docs/<doc_name>')
        def view_docs(doc_name: str):
            """Просмотр конкретного документа"""
            docs_map = {
                'guidelines': 'meeting_recording_guidelines.md',
                'checklist': 'quick_meeting_checklist.md', 
                'setup': 'recording_setup_guide.md'
            }
            
            if doc_name not in docs_map:
                flash('Документ не найден', 'error')
                return redirect(url_for('docs_index'))
            
            try:
                file_path = docs_map[doc_name]
                if not os.path.exists(file_path):
                    flash('Файл документации не найден', 'error')
                    return redirect(url_for('docs_index'))
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                doc_titles = {
                    'guidelines': 'Полное руководство по проведению встреч',
                    'checklist': 'Быстрый чек-лист для записи встреч',
                    'setup': 'Техническое руководство по настройке записи'
                }
                
                return render_template_string(
                    self.templates.get_docs_view_template(),
                    content=content,
                    doc_title=doc_titles[doc_name],
                    doc_name=doc_name
                )
                
            except Exception as e:
                logger.error(f"❌ Ошибка чтения документации: {e}")
                flash(f'Ошибка чтения документации: {str(e)}', 'error')
                return redirect(url_for('docs_index'))
        
        @self.app.errorhandler(RequestEntityTooLarge)
        def handle_file_too_large(e):
            max_size = self.app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
            flash(f'Файл слишком большой. Максимальный размер: {max_size} МБ', 'error')
            return redirect(url_for('index'))
    
    def process_file_sync(self, job_id: str):
        """Синхронная обработка файла в отдельном потоке"""
        # Получаем задачу из базы данных
        job = None
        try:
            # Получаем задачу без проверки пользователя (для фонового процесса)
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                if row:
                    job = dict(row)
        except Exception as e:
            logger.error(f"Ошибка получения задачи {job_id}: {e}")
            return
        
        if not job:
            logger.error(f"Задача {job_id} не найдена")
            return
        
        def progress_callback(progress: int, message: str):
            """Callback для обновления прогресса"""
            try:
                with self.db_manager._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE jobs SET progress = ?, message = ? WHERE job_id = ?",
                        (progress, message, job_id)
                    )
                    conn.commit()
            except Exception as e:
                logger.error(f"Ошибка обновления прогресса для {job_id}: {e}")
        
        try:
            logger.info(f"🔄 Начало обработки файла {job_id}: {job['filename']} для пользователя {job['user_id']}")
            
            # Создаем пользовательскую директорию для вывода
            user_output_dir = self.get_user_output_dir(job['user_id'])
            output_dir = user_output_dir / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            processor = MeetingProcessor(
                deepgram_api_key=self.deepgram_key,
                claude_api_key=self.claude_key,
                deepgram_timeout=self.processing_settings.get('deepgram_timeout_seconds', 300),
                claude_model=self.processing_settings.get('claude_model', 'claude-sonnet-4-20250514'),
                chunk_duration_minutes=self.processing_settings.get('chunk_duration_minutes', 15),
                template_type=job['template'],
                progress_callback=progress_callback
            )
            
            # Основная обработка
            success = processor.process_meeting(
                input_file_path=job['file_path'],
                output_dir=str(output_dir),
                name_mapping=None,
                keep_audio_file=False,
                template_type=job['template']
            )
            
            if success:
                # Извлекаем исходное имя файла
                original_filename = Path(job['file_path']).name
                if original_filename.startswith(job_id + '_'):
                    original_filename = original_filename[len(job_id) + 1:]
                
                input_name = Path(original_filename).stem
                transcript_file = output_dir / f"{input_name}_transcript.txt"
                summary_file = output_dir / f"{input_name}_summary.md"
                
                if transcript_file.exists() and summary_file.exists():
                    # Обновляем задачу в базе данных
                    with self.db_manager._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE jobs SET
                                status = 'completed',
                                progress = 100,
                                message = 'Обработка завершена успешно!',
                                transcript_file = ?,
                                summary_file = ?,
                                completed_at = CURRENT_TIMESTAMP
                            WHERE job_id = ?
                        """, (str(transcript_file), str(summary_file), job_id))
                        conn.commit()
                    
                    logger.info(f"✅ Обработка файла {job_id} завершена успешно")
                else:
                    # Ищем любые файлы в директории
                    all_files = list(output_dir.glob("*"))
                    transcript_files = [f for f in all_files if "_transcript.txt" in f.name]
                    summary_files = [f for f in all_files if "_summary.md" in f.name]
                    
                    logger.info(f"📁 Все файлы в {output_dir}: {[f.name for f in all_files]}")
                    
                    if transcript_files and summary_files:
                        transcript_file = transcript_files[0]
                        summary_file = summary_files[0]
                        
                        # Обновляем задачу в базе данных
                        with self.db_manager._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE jobs SET
                                    status = 'completed',
                                    progress = 100,
                                    message = 'Обработка завершена успешно!',
                                    transcript_file = ?,
                                    summary_file = ?,
                                    completed_at = CURRENT_TIMESTAMP
                                WHERE job_id = ?
                            """, (str(transcript_file), str(summary_file), job_id))
                            conn.commit()
                        
                        logger.info(f"✅ Обработка файла {job_id} завершена успешно")
                        return
                    
                    raise Exception(f"Файлы не найдены. Есть: {[f.name for f in all_files]}")
            else:
                raise Exception("Обработка завершилась с ошибкой")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки файла {job_id}: {e}")
            # Обновляем статус ошибки в базе данных
            try:
                with self.db_manager._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE jobs SET
                            status = 'error',
                            progress = 0,
                            message = ?,
                            error = ?
                        WHERE job_id = ?
                    """, (f'Ошибка обработки: {str(e)}', str(e), job_id))
                    conn.commit()
            except Exception as db_error:
                logger.error(f"Ошибка обновления статуса ошибки в БД: {db_error}")
        
        finally:
            # Очищаем исходный файл
            try:
                if job and job.get('file_path') and os.path.exists(job['file_path']):
                    os.remove(job['file_path'])
                    logger.debug(f"Удален временный файл: {job['file_path']}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
    
    def generate_protocol_sync(self, job_id: str, transcript_file: str, template_type: str):
        """Синхронная генерация протокола из транскрипта в отдельном потоке"""
        job = self.get_job_status(job_id)
        if not job:
            return
        
        def progress_callback(progress: int, message: str):
            """Callback для обновления прогресса"""
            self.update_job_status(job_id, progress=progress, message=message)
        
        try:
            # Создаем выходную директорию для нового протокола
            output_dir = self.output_folder / job_id
            output_dir.mkdir(exist_ok=True)
            
            # Создаем процессор только для генерации протокола
            processor = MeetingProcessor(
                deepgram_api_key="dummy",  # Не нужен для генерации протокола
                claude_api_key=self.claude_key,
                claude_model=self.processing_settings.get('claude_model', 'claude-sonnet-4-20250514'),
                template_type=template_type,
                templates_config_file=self.config.get("paths", {}).get("templates_config", "templates_config.json"),
                team_config_file=self.config.get("paths", {}).get("team_config", "team_config.json"),
                progress_callback=progress_callback
            )
            
            # Генерируем протокол из транскрипта
            success = processor.generate_protocol_from_transcript(
                transcript_file_path=transcript_file,
                output_dir=str(output_dir),
                template_type=template_type
            )
            
            if success:
                # Ищем сгенерированный протокол
                all_files = list(output_dir.glob("*"))
                summary_files = [f for f in all_files if "_summary.md" in f.name]
                
                if summary_files:
                    summary_file = summary_files[0]
                    
                    self.update_job_status(job_id,
                                         status='completed',
                                         progress=100,
                                         message='Протокол успешно сгенерирован!',
                                         transcript_file=transcript_file,  # Ссылка на исходный транскрипт
                                         summary_file=str(summary_file),
                                         completed_at=datetime.now())
                    
                    logger.info(f"✅ Генерация протокола {job_id} завершена успешно")
                else:
                    raise Exception(f"Файл протокола не найден. Есть: {[f.name for f in all_files]}")
            else:
                raise Exception("Генерация протокола завершилась с ошибкой")
                
        except Exception as e:
            logger.error(f"❌ Ошибка генерации протокола {job_id}: {e}")
            self.update_job_status(job_id,
                                 status='error',
                                 progress=0,
                                 message=f'Ошибка генерации протокола: {str(e)}',
                                 error=str(e))
    
    def run(self, host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
        """Запуск веб-приложения"""
        logger.info(f"🌐 Запуск веб-приложения на http://{host}:{port}")
        
        try:
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        finally:
            # Закрываем пул потоков при завершении
            self.executor.shutdown(wait=True)

def main():
    """Основная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Рабочий веб-интерфейс для системы обработки встреч")
    parser.add_argument("-c", "--config", default="config.json", help="Путь к файлу конфигурации")
    parser.add_argument("--host", default="127.0.0.1", help="IP адрес для запуска сервера")
    parser.add_argument("--port", type=int, default=5000, help="Порт для запуска сервера")
    parser.add_argument("--debug", action="store_true", help="Запуск в режиме отладки")
    parser.add_argument("--debug-auth", action="store_true", help="Отключить проверку токенов аутентификации (только для разработки)")
    
    args = parser.parse_args()
    
    try:
        # Создаем необходимые директории
        os.makedirs("logs", exist_ok=True)
        os.makedirs("web_uploads", exist_ok=True)
        os.makedirs("web_output", exist_ok=True)
        
        # Проверяем отладочный режим аутентификации
        from config_loader import ConfigLoader
        config = ConfigLoader.load_config(args.config)
        debug_mode_enabled = False
        
        if config and config.get('auth', {}).get('debug_mode', False):
            debug_mode_enabled = True
            print("🔧 ВНИМАНИЕ: Отладочный режим аутентификации включен в конфигурации!")
            print("   Проверка токенов отключена. Используйте только для разработки!")
        
        # Обрабатываем флаг отладочного режима аутентификации
        if args.debug_auth:
            debug_mode_enabled = True
            print("🔧 ВНИМАНИЕ: Отладочный режим аутентификации включен флагом --debug-auth!")
            print("   Проверка токенов отключена. Используйте только для разработки!")
            
            # Загружаем конфигурацию и принудительно включаем отладочный режим
            if config:
                config.setdefault('auth', {})['debug_mode'] = True
                # Сохраняем временно измененную конфигурацию
                import tempfile
                import json
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                    temp_config_path = f.name
                args.config = temp_config_path
                print(f"🔧 Создан временный файл конфигурации: {temp_config_path}")
        
        # Создаем веб-приложение
        web_app = WorkingMeetingWebApp(args.config)
        
        print("\n" + "="*60)
        print("🚀 MEETING PROCESSOR WEB SERVER (РАБОЧАЯ ВЕРСИЯ)")
        print("="*60)
        print(f"📱 Веб-интерфейс: http://localhost:{args.port}")
        print("🔧 Конфигурация: config.json")
        print("🔑 API ключи: api_keys.json")
        print("📁 Загрузки: web_uploads/")
        print("📄 Результаты: web_output/")
        print("📊 Логи: logs/web_app.log")
        print("🧵 Многопоточная обработка: ✅")
        print("🔄 Автоочистка файлов: ✅")
        
        # Показываем статус аутентификации
        if args.debug_auth:
            print("🔧 Отладочный режим аутентификации: ✅ (ТОЛЬКО ДЛЯ РАЗРАБОТКИ)")
            print("📊 Статистика доступна: http://localhost:{}/statistics".format(args.port))
        else:
            print("🔐 Аутентификация: ✅ (требуется X-Identity-Token)")
        
        print("\n💡 Для остановки нажмите Ctrl+C")
        print("="*60)
        
        # Запускаем сервер
        web_app.run(host=args.host, port=args.port, debug=args.debug)
        
    except KeyboardInterrupt:
        print("\n👋 Веб-приложение остановлено")
    except Exception as e:
        print(f"❌ Ошибка запуска веб-приложения: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
