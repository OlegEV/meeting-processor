#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
"""

import os
import sys
from pathlib import Path

# Добавляем текущую директорию в путь для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import ConfigLoader
from database import create_database_manager

def init_database(config_file: str = "config.json"):
    """Инициализирует базу данных"""
    
    print("🗄️  Инициализация базы данных")
    print("=" * 40)
    
    try:
        # Загружаем конфигурацию
        print("📋 Загрузка конфигурации...")
        config = ConfigLoader.load_config(config_file)
        if not config:
            raise Exception(f"Не удалось загрузить конфигурацию из {config_file}")
        
        print(f"✅ Конфигурация загружена из {config_file}")
        
        # Создаем менеджер базы данных
        print("🔧 Создание менеджера базы данных...")
        db_manager = create_database_manager(config)
        
        # Получаем информацию о базе данных
        db_info = db_manager.get_database_info()
        
        print("✅ База данных успешно инициализирована!")
        print("\n📊 Информация о базе данных:")
        print(f"   Путь: {db_info['db_path']}")
        print(f"   Размер: {db_info['db_size_mb']} МБ")
        print(f"   Пользователей: {db_info['users_count']}")
        print(f"   Задач: {db_info['jobs_count']}")
        print(f"   Резервное копирование: {'включено' if db_info['backup_enabled'] else 'отключено'}")
        
        # Создаем тестовых пользователей если база пустая
        if db_info['users_count'] == 0:
            print("\n👥 Создание тестовых пользователей...")
            
            test_users = [
                {
                    'user_id': 'demo_user',
                    'email': 'demo@example.com',
                    'name': 'Demo User'
                },
                {
                    'user_id': 'test_admin',
                    'email': 'admin@example.com', 
                    'name': 'Test Admin'
                }
            ]
            
            for user_data in test_users:
                try:
                    db_manager.create_user(user_data)
                    print(f"   ✅ Создан пользователь: {user_data['name']} ({user_data['user_id']})")
                except Exception as e:
                    print(f"   ⚠️  Ошибка создания пользователя {user_data['user_id']}: {e}")
        
        # Создаем необходимые директории
        print("\n📁 Создание директорий...")
        
        directories = [
            "web_uploads",
            "web_output", 
            "logs"
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
            print(f"   ✅ Директория: {directory}")
        
        print("\n🎉 Инициализация завершена успешно!")
        print("\n💡 Следующие шаги:")
        print("   1. Запустите веб-приложение: python run_web.py")
        print("   2. Протестируйте аутентификацию: python test_auth.py")
        print("   3. Откройте http://localhost:5000 в браузере")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
        return False

def backup_database(config_file: str = "config.json"):
    """Создает резервную копию базы данных"""
    
    print("💾 Создание резервной копии базы данных")
    print("=" * 45)
    
    try:
        # Загружаем конфигурацию
        config = ConfigLoader.load_config(config_file)
        if not config:
            raise Exception(f"Не удалось загрузить конфигурацию из {config_file}")
        
        # Создаем менеджер базы данных
        db_manager = create_database_manager(config)
        
        # Создаем резервную копию
        backup_path = db_manager.backup_database()
        
        print(f"✅ Резервная копия создана: {backup_path}")
        
        # Получаем размер резервной копии
        backup_size = os.path.getsize(backup_path) / (1024 * 1024)
        print(f"📊 Размер резервной копии: {backup_size:.2f} МБ")
        
        return backup_path
        
    except Exception as e:
        print(f"❌ Ошибка создания резервной копии: {e}")
        return None

def check_database_status(config_file: str = "config.json"):
    """Проверяет статус базы данных"""
    
    print("🔍 Проверка статуса базы данных")
    print("=" * 35)
    
    try:
        # Загружаем конфигурацию
        config = ConfigLoader.load_config(config_file)
        if not config:
            raise Exception(f"Не удалось загрузить конфигурацию из {config_file}")
        
        db_config = config.get('database', {})
        db_path = db_config.get('path', 'meeting_processor.db')
        
        # Проверяем существование файла базы данных
        if not os.path.exists(db_path):
            print(f"❌ Файл базы данных не найден: {db_path}")
            print("💡 Запустите: python init_database.py")
            return False
        
        # Создаем менеджер базы данных
        db_manager = create_database_manager(config)
        
        # Получаем информацию о базе данных
        db_info = db_manager.get_database_info()
        
        print("✅ База данных найдена и доступна")
        print(f"\n📊 Статистика:")
        print(f"   Путь: {db_info['db_path']}")
        print(f"   Размер: {db_info['db_size_mb']} МБ")
        print(f"   Пользователей: {db_info['users_count']}")
        print(f"   Задач: {db_info['jobs_count']}")
        
        # Проверяем последних пользователей
        if db_info['users_count'] > 0:
            print(f"\n👥 Последние пользователи:")
            # Получаем список пользователей (первые 5)
            with db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, email, name, last_login 
                    FROM users 
                    ORDER BY last_login DESC 
                    LIMIT 5
                """)
                users = cursor.fetchall()
                
                for user in users:
                    user_dict = dict(user)
                    last_login = user_dict.get('last_login', 'Никогда')
                    print(f"   • {user_dict['name'] or user_dict['user_id']} ({user_dict['email'] or 'без email'}) - {last_login}")
        
        # Проверяем активные задачи
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count, status 
                FROM jobs 
                GROUP BY status
            """)
            job_stats = cursor.fetchall()
            
            if job_stats:
                print(f"\n📋 Статистика задач:")
                for stat in job_stats:
                    stat_dict = dict(stat)
                    print(f"   • {stat_dict['status']}: {stat_dict['count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки базы данных: {e}")
        return False

def clear_tables(config_file: str = "config.json"):
    """Очищает таблицы с данными (пользователи и задачи)"""
    
    print("🗑️  Очистка таблиц базы данных")
    print("=" * 40)
    
    try:
        # Загружаем конфигурацию
        print("📋 Загрузка конфигурации...")
        config = ConfigLoader.load_config(config_file)
        if not config:
            raise Exception(f"Не удалось загрузить конфигурацию из {config_file}")
        
        print(f"✅ Конфигурация загружена из {config_file}")
        
        # Создаем менеджер базы данных
        print("🔧 Подключение к базе данных...")
        db_manager = create_database_manager(config)
        
        # Получаем информацию о базе данных до очистки
        db_info_before = db_manager.get_database_info()
        print(f"\n📊 Состояние до очистки:")
        print(f"   Пользователей: {db_info_before['users_count']}")
        print(f"   Задач: {db_info_before['jobs_count']}")
        
        # Подтверждение от пользователя
        print(f"\n⚠️  ВНИМАНИЕ: Будут удалены ВСЕ данные из таблиц!")
        print(f"   • Все пользователи ({db_info_before['users_count']} записей)")
        print(f"   • Все задачи ({db_info_before['jobs_count']} записей)")
        
        confirmation = input("\nВы уверены? Введите 'YES' для подтверждения: ")
        if confirmation != 'YES':
            print("❌ Операция отменена пользователем")
            return False
        
        # Очищаем таблицы
        print("\n🗑️  Очистка таблиц...")
        
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            
            # Отключаем проверку внешних ключей для корректного удаления
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Очищаем таблицы в правильном порядке (сначала зависимые)
            tables_to_clear = ['jobs', 'users']
            
            for table in tables_to_clear:
                cursor.execute(f"DELETE FROM {table}")
                deleted_count = cursor.rowcount
                print(f"   ✅ Таблица '{table}': удалено {deleted_count} записей")
            
            # Сбрасываем счетчики автоинкремента (если таблица существует)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('jobs', 'users')")
                print(f"   ✅ Сброшены счетчики автоинкремента")
            
            # Включаем обратно проверку внешних ключей
            cursor.execute("PRAGMA foreign_keys = ON")
            
            conn.commit()
        
        # Получаем информацию о базе данных после очистки
        db_info_after = db_manager.get_database_info()
        print(f"\n📊 Состояние после очистки:")
        print(f"   Пользователей: {db_info_after['users_count']}")
        print(f"   Задач: {db_info_after['jobs_count']}")
        
        print("\n🎉 Очистка таблиц завершена успешно!")
        print("\n💡 Следующие шаги:")
        print("   1. Для создания тестовых данных: python init_database.py init")
        print("   2. Для проверки статуса: python init_database.py status")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка очистки таблиц: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Управление базой данных")
    parser.add_argument("-c", "--config", default="config.json", help="Путь к файлу конфигурации")
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда инициализации
    init_parser = subparsers.add_parser('init', help='Инициализация базы данных')
    
    # Команда резервного копирования
    backup_parser = subparsers.add_parser('backup', help='Создание резервной копии')
    
    # Команда проверки статуса
    status_parser = subparsers.add_parser('status', help='Проверка статуса базы данных')
    
    # Команда очистки таблиц
    clear_parser = subparsers.add_parser('clear', help='Очистка таблиц с данными')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        success = init_database(args.config)
        sys.exit(0 if success else 1)
    elif args.command == 'backup':
        backup_path = backup_database(args.config)
        sys.exit(0 if backup_path else 1)
    elif args.command == 'status':
        success = check_database_status(args.config)
        sys.exit(0 if success else 1)
    elif args.command == 'clear':
        success = clear_tables(args.config)
        sys.exit(0 if success else 1)
    else:
        # По умолчанию выполняем инициализацию
        print("Команда не указана, выполняется инициализация...")
        success = init_database(args.config)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()