#!/usr/bin/env python3
"""
Скрипт для добавления тестовой задачи в веб-приложение
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Добавляем путь к модулям
sys.path.append('.')

from run_web import WorkingMeetingWebApp

def add_test_job():
    """Добавляет тестовую завершенную задачу"""
    
    # Создаем экземпляр веб-приложения
    app = WorkingMeetingWebApp()
    
    # Создаем тестовую задачу
    test_job_id = "test-job-123"
    
    with app.jobs_lock:
        app.processing_jobs[test_job_id] = {
            'status': 'completed',
            'filename': 'test_meeting.mp3',
            'template': 'standard',
            'file_path': 'web_uploads/test_meeting.mp3',
            'created_at': datetime.now(),
            'progress': 100,
            'message': 'Обработка завершена успешно!',
            'transcript_file': str(Path('web_output/test-job-123/test_meeting_transcript.txt').absolute()),
            'summary_file': str(Path('web_output/test-job-123/test_meeting_summary.md').absolute()),
            'completed_at': datetime.now()
        }
    
    print(f"✅ Тестовая задача {test_job_id} добавлена")
    print(f"📄 Транскрипт: {app.processing_jobs[test_job_id]['transcript_file']}")
    print(f"📋 Протокол: {app.processing_jobs[test_job_id]['summary_file']}")
    
    return app

if __name__ == "__main__":
    add_test_job()
