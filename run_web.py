#!/usr/bin/env python3
"""
Рабочая версия веб-приложения для обработки встреч
Полностью протестирована и исправлена
"""

import os
import sys
import tempfile
import shutil
import uuid
import time
import threading
from pathlib import Path
from typing import Dict, Optional
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
except ImportError as e:
    print(f"❌ Ошибка импорта модулей: {e}")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # Настройки приложения
        self.setup_app_config()
        
        # Хранилище задач и защита от race conditions
        self.processing_jobs = {}
        self.jobs_lock = threading.Lock()
        
        # Пул потоков для обработки файлов
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="FileProcessor")
        
        # Создаем необходимые директории
        self.upload_folder = Path("web_uploads")
        self.output_folder = Path("web_output")
        self.upload_folder.mkdir(exist_ok=True)
        self.output_folder.mkdir(exist_ok=True)
        
        # Настраиваем маршруты
        self.setup_routes()
        
        logger.info("🌐 Веб-приложение инициализировано")
    
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
        """Безопасно обновляет статус задачи"""
        with self.jobs_lock:
            if job_id in self.processing_jobs:
                self.processing_jobs[job_id].update(kwargs)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Безопасно получает статус задачи"""
        with self.jobs_lock:
            return self.processing_jobs.get(job_id, {}).copy() if job_id in self.processing_jobs else None
    
    def setup_routes(self):
        """Настраивает маршруты приложения"""
        
        @self.app.route('/health')
        def health_check():
            """Health check для мониторинга"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
                'active_jobs': len([j for j in self.processing_jobs.values() 
                                  if j['status'] in ['uploaded', 'processing']])
            })        
            
        @self.app.route('/')
        def index():
            """Главная страница"""
            templates = self.get_available_templates()
            max_size_mb = self.app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
            
            return render_template_string(
                self.get_index_template(),
                templates=templates,
                max_size_mb=max_size_mb,
                accept_string=self.accept_string,
                formats_display=self.formats_display
            )
        
        @self.app.route('/upload', methods=['POST'])
        def upload_file():
            """Обработка загрузки файла"""
            try:
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
                
                # Сохраняем файл
                filename = secure_filename(file.filename)
                file_path = self.upload_folder / f"{job_id}_{filename}"
                file.save(str(file_path))
                
                # Создаем задачу
                with self.jobs_lock:
                    self.processing_jobs[job_id] = {
                        'status': 'uploaded',
                        'filename': filename,
                        'template': template_type,
                        'file_path': str(file_path),
                        'created_at': datetime.now(),
                        'progress': 0,
                        'message': 'Файл загружен, ожидает обработки'
                    }
                
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
        def status(job_id: str):
            """Страница статуса обработки"""
            job = self.get_job_status(job_id)
            if not job:
                flash('Задача не найдена', 'error')
                return redirect(url_for('index'))
            
            templates = self.get_available_templates()
            
            return render_template_string(
                self.get_status_template(),
                job_id=job_id,
                job=job,
                templates=templates
            )
        
        @self.app.route('/api/status/<job_id>')
        def api_status(job_id: str):
            """API для получения статуса задачи"""
            job = self.get_job_status(job_id)
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            return jsonify({
                'status': job['status'],
                'progress': job['progress'],
                'message': job['message'],
                'filename': job['filename'],
                'template': job['template']
            })
        
        @self.app.route('/download/<job_id>/<file_type>')
        def download_file(job_id: str, file_type: str):
            """Скачивание результирующих файлов"""
            job = self.get_job_status(job_id)
            if not job:
                flash('Задача не найдена', 'error')
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
        def view_file(job_id: str, file_type: str):
            """Просмотр файлов в веб-интерфейсе"""
            job = self.get_job_status(job_id)
            if not job:
                flash('Задача не найдена', 'error')
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
                    self.get_view_template(),
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
        
        @self.app.route('/jobs')
        def jobs_list():
            """Список всех задач"""
            jobs = []
            with self.jobs_lock:
                for job_id, job_data in self.processing_jobs.items():
                    jobs.append({
                        'id': job_id,
                        'filename': job_data['filename'],
                        'status': job_data['status'],
                        'template': job_data['template'],
                        'created_at': job_data['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                        'progress': job_data['progress']
                    })
            
            jobs.sort(key=lambda x: x['created_at'], reverse=True)
            return render_template_string(self.get_jobs_template(), jobs=jobs)
        
        @self.app.errorhandler(RequestEntityTooLarge)
        def handle_file_too_large(e):
            max_size = self.app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
            flash(f'Файл слишком большой. Максимальный размер: {max_size} МБ', 'error')
            return redirect(url_for('index'))
    
    def process_file_sync(self, job_id: str):
        """Синхронная обработка файла в отдельном потоке"""
        job = self.get_job_status(job_id)
        if not job:
            return
        
        try:
            self.update_job_status(job_id, status='processing', progress=10, message='Инициализация обработки...')
            
            output_dir = self.output_folder / job_id
            output_dir.mkdir(exist_ok=True)
            
            processor = MeetingProcessor(
                deepgram_api_key=self.deepgram_key,
                claude_api_key=self.claude_key,
                deepgram_timeout=self.processing_settings.get('deepgram_timeout_seconds', 300),
                claude_model=self.processing_settings.get('claude_model', 'claude-sonnet-4-20250514'),
                chunk_duration_minutes=self.processing_settings.get('chunk_duration_minutes', 15),
                template_type=job['template']
            )
            
            self.update_job_status(job_id, progress=30, message='Подготовка аудио для транскрипции...')
            time.sleep(1)
            
            self.update_job_status(job_id, progress=50, message='Транскрибирование аудио...')
            
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
                    self.update_job_status(job_id,
                                         status='completed',
                                         progress=100,
                                         message='Обработка завершена успешно!',
                                         transcript_file=str(transcript_file),
                                         summary_file=str(summary_file),
                                         completed_at=datetime.now())
                    
                    logger.info(f"✅ Обработка файла {job_id} завершена успешно")
                else:
                    # Ищем любые файлы в директории
                    all_files = list(output_dir.glob("*"))
                    transcript_files = [f for f in all_files if "_transcript.txt" in f.name]
                    summary_files = [f for f in all_files if "_summary.md" in f.name]
                    
                    logger.error(f"📁 Все файлы в {output_dir}: {[f.name for f in all_files]}")
                    logger.error(f"📄 Транскрипты: {[f.name for f in transcript_files]}")
                    logger.error(f"📋 Протоколы: {[f.name for f in summary_files]}")
                    
                    if transcript_files and summary_files:
                        transcript_file = transcript_files[0]
                        summary_file = summary_files[0]
                        
                        logger.info(f"✅ Найдены файлы: {transcript_file.name}, {summary_file.name}")
                        
                        self.update_job_status(job_id,
                                             status='completed',
                                             progress=100,
                                             message='Обработка завершена успешно!',
                                             transcript_file=str(transcript_file),
                                             summary_file=str(summary_file),
                                             completed_at=datetime.now())
                        
                        logger.info(f"✅ Обработка файла {job_id} завершена успешно")
                        return
                    
                    raise Exception(f"Файлы не найдены. Есть: {[f.name for f in all_files]}")
            else:
                raise Exception("Обработка завершилась с ошибкой")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки файла {job_id}: {e}")
            self.update_job_status(job_id,
                                 status='error',
                                 progress=0,
                                 message=f'Ошибка обработки: {str(e)}',
                                 error=str(e))
        
        finally:
            # Очищаем исходный файл
            try:
                if os.path.exists(job['file_path']):
                    os.remove(job['file_path'])
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
    
    def get_index_template(self):
        """Возвращает HTML шаблон главной страницы"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meeting Processor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container">
            <span class="navbar-brand"><i class="fas fa-microphone me-2"></i>Meeting Processor</span>
            <div class="navbar-nav">
                <a class="nav-link" href="/jobs"><i class="fas fa-list me-1"></i>Все задачи</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white">
                        <h4><i class="fas fa-upload me-2"></i>Загрузка файла для обработки</h4>
                    </div>
                    <div class="card-body">
                        <form method="POST" action="/upload" enctype="multipart/form-data">
                            <div class="mb-3">
                                <label for="template" class="form-label">Шаблон протокола:</label>
                                <select class="form-select" name="template" required>
                                    {% for template_id, description in templates.items() %}
                                        <option value="{{ template_id }}" {% if template_id == 'standard' %}selected{% endif %}>
                                            {{ template_id.title() }} - {{ description }}
                                        </option>
                                    {% endfor %}
                                </select>
                            </div>

                            <div class="mb-3">
                                <label for="file" class="form-label">Выберите файл:</label>
                                <input type="file" class="form-control" name="file" accept="{{ accept_string }}" required>
                                <div class="form-text">
                                    Максимальный размер: {{ max_size_mb }} МБ<br>
                                    Поддерживаемые форматы: {{ formats_display }}
                                </div>
                            </div>

                            <button type="submit" class="btn btn-success btn-lg w-100">
                                <i class="fas fa-rocket me-2"></i>Начать обработку
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-5">
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-microphone fa-3x text-primary mb-3"></i>
                        <h5>Транскрипция</h5>
                        <p class="text-muted">Автоматическое преобразование речи в текст</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-file-alt fa-3x text-success mb-3"></i>
                        <h5>Протоколы</h5>
                        <p class="text-muted">Структурированные протоколы встреч</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-users fa-3x text-info mb-3"></i>
                        <h5>Участники</h5>
                        <p class="text-muted">Автоматическая идентификация спикеров</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        '''
    
    def get_view_template(self):
        """Возвращает HTML шаблон для просмотра файлов"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ file_title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    {% if is_markdown %}
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        .markdown-content {
            line-height: 1.6;
        }
        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
            color: #0d6efd;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }
        .markdown-content ul, .markdown-content ol {
            margin-bottom: 1rem;
        }
        .markdown-content li {
            margin-bottom: 0.25rem;
        }
        .markdown-content code {
            background-color: #f8f9fa;
            padding: 0.125rem 0.25rem;
            border-radius: 0.25rem;
        }
        .markdown-content blockquote {
            border-left: 4px solid #0d6efd;
            padding-left: 1rem;
            margin: 1rem 0;
            background-color: #f8f9fa;
            padding: 0.5rem 1rem;
        }
    </style>
    {% endif %}
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-microphone me-2"></i>Meeting Processor</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/jobs"><i class="fas fa-list me-1"></i>Все задачи</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="card shadow">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h4><i class="fas fa-file-alt me-2"></i>{{ file_title }}</h4>
                <div>
                    <a href="/download/{{ job_id }}/{{ file_type }}" class="btn btn-light btn-sm me-2">
                        <i class="fas fa-download me-1"></i>Скачать
                    </a>
                    <a href="/status/{{ job_id }}" class="btn btn-outline-light btn-sm">
                        <i class="fas fa-arrow-left me-1"></i>Назад
                    </a>
                </div>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <small class="text-muted">
                        <i class="fas fa-file me-1"></i>Файл: {{ filename }}
                    </small>
                </div>
                
                {% if is_markdown %}
                    <div id="markdown-content" class="markdown-content"></div>
                    <script>
                        const markdownText = {{ content|tojson }};
                        document.getElementById('markdown-content').innerHTML = marked.parse(markdownText);
                    </script>
                {% else %}
                    <pre class="bg-light p-3 rounded" style="white-space: pre-wrap; max-height: 70vh; overflow-y: auto;">{{ content }}</pre>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        '''
    
    def get_status_template(self):
        """Возвращает HTML шаблон страницы статуса"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Статус обработки</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-microphone me-2"></i>Meeting Processor</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/jobs"><i class="fas fa-list me-1"></i>Все задачи</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white">
                        <h4><i class="fas fa-tasks me-2"></i>Статус обработки</h4>
                    </div>
                    <div class="card-body text-center">
                        <div class="mb-3">
                            {% if job.status == 'completed' %}
                                <i class="fas fa-check-circle fa-4x text-success"></i>
                            {% elif job.status == 'error' %}
                                <i class="fas fa-exclamation-circle fa-4x text-danger"></i>
                            {% else %}
                                <i class="fas fa-cog fa-spin fa-4x text-primary"></i>
                            {% endif %}
                        </div>

                        <h5>{{ job.filename }}</h5>
                        <p class="text-muted">Шаблон: {{ job.template }}</p>

                        <div class="progress mb-3" style="height: 30px;">
                            <div class="progress-bar 
                                {% if job.status == 'completed' %}bg-success{% elif job.status == 'error' %}bg-danger{% else %}bg-primary progress-bar-animated{% endif %}" 
                                style="width: {{ job.progress }}%">
                                {{ job.progress }}%
                            </div>
                        </div>

                        <div class="alert 
                            {% if job.status == 'completed' %}alert-success{% elif job.status == 'error' %}alert-danger{% else %}alert-info{% endif %}">
                            {{ job.message }}
                        </div>

                        {% if job.status == 'completed' %}
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <a href="/view/{{ job_id }}/transcript" class="btn btn-outline-info w-100 mb-2">
                                        <i class="fas fa-eye me-2"></i>Просмотреть транскрипт
                                    </a>
                                </div>
                                <div class="col-md-6">
                                    <a href="/view/{{ job_id }}/summary" class="btn btn-info w-100 mb-2">
                                        <i class="fas fa-eye me-2"></i>Просмотреть протокол
                                    </a>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <a href="/download/{{ job_id }}/transcript" class="btn btn-outline-primary w-100 mb-2">
                                        <i class="fas fa-file-alt me-2"></i>Скачать транскрипт
                                    </a>
                                </div>
                                <div class="col-md-6">
                                    <a href="/download/{{ job_id }}/summary" class="btn btn-primary w-100 mb-2">
                                        <i class="fas fa-file-download me-2"></i>Скачать протокол
                                    </a>
                                </div>
                            </div>
                            <a href="/" class="btn btn-success">
                                <i class="fas fa-plus me-2"></i>Обработать еще файл
                            </a>
                        {% elif job.status == 'error' %}
                            <a href="/" class="btn btn-primary">
                                <i class="fas fa-upload me-2"></i>Попробовать снова
                            </a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        {% if job.status not in ['completed', 'error'] %}
            setInterval(function() {
                fetch('/api/status/{{ job_id }}')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'completed' || data.status === 'error') {
                            location.reload();
                        } else {
                            const progressBar = document.querySelector('.progress-bar');
                            const alertDiv = document.querySelector('.alert');
                            
                            progressBar.style.width = data.progress + '%';
                            progressBar.textContent = data.progress + '%';
                            alertDiv.textContent = data.message;
                        }
                    })
                    .catch(error => console.error('Ошибка обновления статуса:', error));
            }, 2000);
        {% endif %}
    </script>
</body>
</html>
        '''
    
    def get_jobs_template(self):
        """Возвращает HTML шаблон списка задач"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Все задачи</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-microphone me-2"></i>Meeting Processor</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/"><i class="fas fa-upload me-1"></i>Загрузить файл</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="card shadow">
            <div class="card-header bg-primary text-white">
                <h4><i class="fas fa-list me-2"></i>История обработки файлов</h4>
            </div>
            <div class="card-body">
                {% if jobs %}
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead class="table-light">
                                <tr>
                                    <th>Файл</th>
                                    <th>Шаблон</th>
                                    <th>Статус</th>
                                    <th>Прогресс</th>
                                    <th>Дата создания</th>
                                    <th>Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for job in jobs %}
                                    <tr>
                                        <td><i class="fas fa-file me-1"></i>{{ job.filename }}</td>
                                        <td><span class="badge bg-secondary">{{ job.template }}</span></td>
                                        <td>
                                            {% if job.status == 'completed' %}
                                                <span class="badge bg-success"><i class="fas fa-check me-1"></i>Завершено</span>
                                            {% elif job.status == 'error' %}
                                                <span class="badge bg-danger"><i class="fas fa-exclamation me-1"></i>Ошибка</span>
                                            {% elif job.status == 'processing' %}
                                                <span class="badge bg-primary"><i class="fas fa-cog fa-spin me-1"></i>Обработка</span>
                                            {% else %}
                                                <span class="badge bg-warning"><i class="fas fa-clock me-1"></i>Ожидание</span>
                                            {% endif %}
                                        </td>
                                        <td>
                                            <div class="progress" style="height: 20px; width: 100px;">
                                                <div class="progress-bar {% if job.status == 'completed' %}bg-success{% elif job.status == 'error' %}bg-danger{% else %}bg-primary{% endif %}" 
                                                    style="width: {{ job.progress }}%">
                                                    <small>{{ job.progress }}%</small>
                                                </div>
                                            </div>
                                        </td>
                                        <td>{{ job.created_at }}</td>
                                        <td>
                                            <a href="/status/{{ job.id }}" class="btn btn-sm btn-outline-primary">
                                                <i class="fas fa-eye me-1"></i>Подробнее
                                            </a>
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <div class="text-center py-5">
                        <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                        <h5 class="text-muted">Нет обработанных файлов</h5>
                        <p class="text-muted">Загрузите первый файл для начала работы</p>
                        <a href="/" class="btn btn-primary">
                            <i class="fas fa-upload me-2"></i>Загрузить файл
                        </a>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        '''
    
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
    
    args = parser.parse_args()
    
    try:
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
        print("🧵 Многопоточная обработка: ✅")
        print("🔄 Автоочистка файлов: ✅")
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