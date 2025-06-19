#!/usr/bin/env python3
"""
Скрипт для добавления тестовых данных в базу данных
"""

import sqlite3
import uuid
from datetime import datetime, timedelta
import random

def add_test_data():
    """Добавляет тестовые данные в базу данных"""
    
    # Подключаемся к базе данных
    conn = sqlite3.connect('meeting_processor.db')
    cursor = conn.cursor()
    
    # Создаем тестовых пользователей
    users = [
        ('alice', 'alice@company.com', 'Alice Johnson'),
        ('bob', 'bob@company.com', 'Bob Smith'),
        ('charlie', 'charlie@company.com', 'Charlie Brown')
    ]
    
    for user_id, email, name in users:
        cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, email, name, created_at, last_login)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, email, name, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
    
    # Создаем тестовые задачи за последние 30 дней
    templates = ['standard', 'business', 'project', 'standup', 'interview']
    statuses = ['completed', 'completed', 'completed', 'error']  # Больше успешных
    
    for i in range(50):  # 50 тестовых задач
        job_id = str(uuid.uuid4())
        user_id = random.choice([u[0] for u in users])
        template = random.choice(templates)
        status = random.choice(statuses)
        
        # Случайная дата за последние 30 дней
        days_ago = random.randint(0, 30)
        created_at = datetime.utcnow() - timedelta(days=days_ago)
        
        # Если задача завершена, добавляем время завершения
        completed_at = None
        if status == 'completed':
            completed_at = created_at + timedelta(minutes=random.randint(5, 30))
        
        cursor.execute("""
            INSERT OR REPLACE INTO jobs (
                job_id, user_id, filename, template, status, progress, message,
                created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, user_id, f'meeting_{i+1}.mp3', template, status,
            100 if status == 'completed' else 0,
            'Обработка завершена успешно!' if status == 'completed' else 'Ошибка обработки',
            created_at.isoformat(),
            completed_at.isoformat() if completed_at else None
        ))
    
    conn.commit()
    conn.close()
    
    print("✅ Тестовые данные добавлены в базу данных!")
    print(f"   - Пользователи: {len(users)}")
    print(f"   - Задачи: 50")

if __name__ == "__main__":
    add_test_data()