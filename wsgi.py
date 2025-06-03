#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point для производственного развертывания
Meeting Processor Web Application
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

# Создаем logs директорию если её нет
os.makedirs('logs', exist_ok=True)

# Настройка логирования для production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Отключаем логирование werkzeug для избежания конфликтов
logging.getLogger('werkzeug').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

def create_app():
    """Создает и настраивает Flask приложение для production"""
    
    try:
        # Импортируем наше приложение
        from run_web import WorkingMeetingWebApp
        
        # Создаем приложение
        config_file = os.environ.get('MEETING_CONFIG', 'config.json')
        web_app = WorkingMeetingWebApp(config_file)
        
        # Настраиваем для production
        app = web_app.app
        app.config.update(
            SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24)),
            MAX_CONTENT_LENGTH=int(os.environ.get('MAX_UPLOAD_SIZE', 100 * 1024 * 1024)),
            UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', 'web_uploads'),
            OUTPUT_FOLDER=os.environ.get('OUTPUT_FOLDER', 'web_output'),
        )
        
        logger.info("Flask приложение создано успешно")
        return app
        
    except Exception as e:
        logger.error(f"Ошибка создания приложения: {e}")
        raise

# Создаем экземпляр приложения
application = create_app()

# Для совместимости с различными WSGI серверами
app = application

if __name__ == "__main__":
    # Для локального тестирования
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Запуск development сервера на {host}:{port}")
    application.run(host=host, port=port, debug=debug)