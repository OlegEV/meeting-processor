# Руководство по развертыванию системы аутентификации

Пошаговое руководство по развертыванию веб-приложения с поддержкой многопользовательского режима и внешней аутентификации.

## Быстрый старт

### 1. Подготовка окружения

```bash
# Клонирование репозитория (если нужно)
git clone <repository-url>
cd meeting-processor

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Инициализация базы данных

```bash
# Инициализация базы данных и создание тестовых пользователей
python init_database.py init

# Проверка статуса базы данных
python init_database.py status
```

### 3. Запуск приложения

```bash
# Запуск веб-приложения
python run_web.py

# Приложение будет доступно на http://localhost:5000
```

### 4. Тестирование

```bash
# Получение тестовых JWT токенов
python test_auth.py --tokens-only

# Полное тестирование аутентификации
python test_auth.py
```

## Детальное развертывание

### Шаг 1: Проверка зависимостей

Убедитесь, что установлены все необходимые зависимости:

```bash
pip install -r requirements.txt
```

Новые зависимости:
- `PyJWT>=2.8.0` - для работы с JWT токенами

### Шаг 2: Конфигурация

Проверьте файл `config.json`. Новые секции:

```json
{
  "auth": {
    "token_header": "X-Identity-Token",
    "jwt_algorithm": "RS256", 
    "token_validation": {
      "verify_signature": false,
      "verify_exp": true,
      "verify_aud": false
    }
  },
  "database": {
    "type": "sqlite",
    "path": "meeting_processor.db",
    "backup_enabled": true,
    "backup_interval_hours": 24
  },
  "user_files": {
    "base_path": "web_output",
    "structure": "user_based"
  }
}
```

### Шаг 3: Инициализация базы данных

```bash
# Полная инициализация
python init_database.py init

# Только проверка статуса
python init_database.py status

# Создание резервной копии
python init_database.py backup
```

Результат инициализации:
- Создается файл `meeting_processor.db`
- Создаются таблицы `users` и `jobs`
- Добавляются индексы для производительности
- Создаются тестовые пользователи
- Создаются необходимые директории

### Шаг 4: Структура директорий

После инициализации структура будет:

```
meeting-processor/
├── meeting_processor.db          # База данных SQLite
├── web_uploads/                  # Загруженные файлы
├── web_output/                   # Результаты обработки
├── logs/                         # Логи приложения
└── auth/                         # Модуль аутентификации
    database/                     # Модуль базы данных
```

### Шаг 5: Тестирование аутентификации

```bash
# Получение тестовых токенов
python test_auth.py --tokens-only
```

Пример вывода:
```
🔑 Тестовые JWT токены для ручного тестирования:
============================================================

👤 Alice Johnson (alice):
   Email: alice@company.com
   Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJzdWIiOiJhbGljZSIsImlhdCI6MTY0MDk5NTIwMCwiZXhwIjoxNjQxMDgxNjAwLCJlbWFpbCI6ImFsaWNlQGNvbXBhbnkuY29tIiwibmFtZSI6IkFsaWNlIEpvaG5zb24ifQ.
   Заголовок: X-Identity-Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0...
```

### Шаг 6: Запуск приложения

```bash
# Запуск в режиме разработки
python run_web.py

# Запуск на другом порту
python run_web.py --port 8080

# Запуск с отладкой
python run_web.py --debug
```

### Шаг 7: Проверка работоспособности

```bash
# Health check (без аутентификации)
curl http://localhost:5000/health

# Тестирование с токеном
curl -H "X-Identity-Token: YOUR_JWT_TOKEN" http://localhost:5000/

# Полное тестирование
python test_auth.py
```

## Развертывание с Docker

### Шаг 1: Подготовка

```bash
# Убедитесь, что база данных инициализирована
python init_database.py init
```

### Шаг 2: Сборка и запуск

```bash
# Сборка и запуск веб-сервиса
docker-compose up meeting-web

# Запуск в фоновом режиме
docker-compose up -d meeting-web
```

### Шаг 3: Проверка

```bash
# Проверка статуса контейнера
docker-compose ps

# Просмотр логов
docker-compose logs meeting-web

# Health check
curl http://localhost:8001/health
```

## Интеграция с Reverse Proxy

### Настройка Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Аутентификация через внешний IdP
    location /auth {
        # Ваша логика аутентификации
        # Должна устанавливать заголовок X-Identity-Token
    }
    
    # Проксирование к веб-приложению
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Передача токена аутентификации
        proxy_set_header X-Identity-Token $http_x_identity_token;
    }
}
```

### Настройка Apache

```apache
<VirtualHost *:80>
    ServerName your-domain.com
    
    # Проксирование к веб-приложению
    ProxyPass / http://localhost:5000/
    ProxyPassReverse / http://localhost:5000/
    
    # Передача заголовков
    ProxyPreserveHost On
    ProxyPassReverse / http://localhost:5000/
    
    # Передача токена аутентификации
    ProxyPassReverse / http://localhost:5000/
</VirtualHost>
```

## Мониторинг и обслуживание

### Логирование

Логи записываются в `logs/web_app.log`:

```bash
# Просмотр логов в реальном времени
tail -f logs/web_app.log

# Поиск ошибок аутентификации
grep "auth" logs/web_app.log

# Поиск ошибок базы данных
grep "database" logs/web_app.log
```

### Резервное копирование

```bash
# Создание резервной копии базы данных
python init_database.py backup

# Автоматическое резервное копирование (cron)
0 2 * * * cd /path/to/meeting-processor && python init_database.py backup
```

### Мониторинг производительности

```bash
# Проверка размера базы данных
python init_database.py status

# Мониторинг активных соединений
netstat -an | grep :5000

# Проверка использования диска
du -sh web_output/ web_uploads/ logs/
```

## Безопасность

### Рекомендации по безопасности

1. **Файловые права доступа**:
```bash
chmod 600 meeting_processor.db
chmod 700 web_uploads/ web_output/
```

2. **Переменные окружения**:
```bash
export DEEPGRAM_API_KEY="your-key"
export CLAUDE_API_KEY="your-key"
```

3. **Firewall**:
```bash
# Разрешить только локальные соединения
ufw allow from 127.0.0.1 to any port 5000
```

### Аудит безопасности

```bash
# Проверка прав доступа к файлам
find . -name "*.db" -exec ls -la {} \;

# Проверка открытых портов
netstat -tulpn | grep :5000

# Анализ логов на подозрительную активность
grep -i "error\|fail\|unauthorized" logs/web_app.log
```

## Troubleshooting

### Проблема: База данных не создается

```bash
# Проверка прав доступа
ls -la meeting_processor.db

# Пересоздание базы данных
rm meeting_processor.db
python init_database.py init
```

### Проблема: Ошибки аутентификации

```bash
# Проверка формата токена
python test_auth.py --tokens-only

# Проверка конфигурации
grep -A 10 '"auth"' config.json

# Проверка логов
grep "auth" logs/web_app.log | tail -20
```

### Проблема: Файлы не найдены

```bash
# Проверка структуры директорий
find web_output/ -type d | head -10

# Проверка прав доступа
ls -la web_output/

# Пересоздание директорий
python init_database.py init
```

### Проблема: Высокое использование памяти

```bash
# Очистка старых задач (старше 30 дней)
python -c "
from database import create_database_manager
from config_loader import ConfigLoader
config = ConfigLoader.load_config('config.json')
db = create_database_manager(config)
# Здесь можно добавить логику очистки
"
```

## Обновление системы

### Обновление с предыдущих версий

1. **Создание резервной копии**:
```bash
python init_database.py backup
cp -r web_output/ web_output_backup/
```

2. **Обновление кода**:
```bash
git pull origin main
pip install -r requirements.txt
```

3. **Миграция данных**:
```bash
python init_database.py init
```

4. **Проверка работоспособности**:
```bash
python test_auth.py
```

### Откат изменений

```bash
# Восстановление базы данных
cp meeting_processor.db.backup_YYYYMMDD_HHMMSS meeting_processor.db

# Восстановление файлов
rm -rf web_output/
mv web_output_backup/ web_output/

# Перезапуск приложения
python run_web.py
```

## Производительность

### Оптимизация базы данных

```sql
-- Анализ производительности запросов
EXPLAIN QUERY PLAN SELECT * FROM jobs WHERE user_id = 'user123';

-- Обновление статистики
ANALYZE;

-- Очистка базы данных
VACUUM;
```

### Мониторинг ресурсов

```bash
# Использование CPU и памяти
top -p $(pgrep -f "python run_web.py")

# Использование диска
df -h
du -sh meeting_processor.db web_output/ web_uploads/

# Количество открытых файлов
lsof -p $(pgrep -f "python run_web.py") | wc -l
```

## Поддержка

### Сбор диагностической информации

```bash
# Создание отчета о системе
python -c "
import sys
print('Python версия:', sys.version)
print('Платформа:', sys.platform)
"

python init_database.py status
python test_auth.py --url http://localhost:5000
```

### Контакты для поддержки

При возникновении проблем:

1. Проверьте логи в `logs/web_app.log`
2. Запустите диагностические скрипты
3. Создайте issue с подробным описанием проблемы
4. Приложите релевантные логи и конфигурацию

---

**Успешного развертывания! 🚀**