# 🐳 Meeting Telegram Bot - Docker Setup

## 🚀 Быстрый старт

### 1. Предварительные требования

- **Windows 10/11** с включенной виртуализацией
- **Docker Desktop** - [скачать здесь](https://www.docker.com/products/docker-desktop/)
- **Git** (опционально) - для клонирования репозитория

### 2. Установка Docker Desktop

1. Скачайте Docker Desktop с официального сайта
2. Запустите установщик и следуйте инструкциям
3. После установки перезагрузите компьютер
4. Запустите Docker Desktop и дождитесь полной загрузки

### 3. Первоначальная настройка

```batch
# Запустите скрипт первоначальной настройки
setup_bot.bat
```

Скрипт автоматически:
- Проверит наличие Docker Desktop
- Создаст необходимые директории
- Создаст конфигурационные файлы
- Поможет настроить API ключи
- Соберет Docker образ

### 4. Настройка API ключей

Отредактируйте файл `.env`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
```

### 5. Запуск бота

```batch
# Запустите интерактивный скрипт управления
run_bot.bat
```

## 📁 Структура проекта

```
meeting-bot/
├── 🐳 Docker файлы
│   ├── Dockerfile              # Конфигурация Docker образа
│   ├── docker-compose.yml      # Docker Compose конфигурация
│   ├── requirements.txt        # Python зависимости
│   └── .dockerignore           # Исключения для Docker
│
├── ⚙️ Конфигурация (в корне)
│   ├── .env                    # Переменные окружения
│   ├── .env.example            # Пример файла окружения
│   ├── bot_config.json         # Настройки бота
│   ├── config.json             # Основная конфигурация
│   ├── templates_config.json   # Конфигурация шаблонов
│   ├── names_config.json       # Настройки имен
│   └── team_config.json        # Настройки команды
│
├── 📝 Python код
│   ├── telegram_bot.py         # Основной файл бота
│   ├── meeting_processor.py    # Обработчик встреч
│   └── *.py                    # Другие модули
│
├── 🗂️ Рабочие директории
│   ├── logs/                   # Логи (монтируется в контейнер)
│   ├── temp_files/             # Временные файлы
│   └── output/                 # Результаты обработки
│
└── 🛠️ Windows скрипты
    ├── setup_bot.bat           # Первоначальная настройка
    └── run_bot.bat             # Управление ботом
```

## 🎛️ Управление ботом

### Запуск в фоне
```batch
docker-compose up -d
```

### Просмотр логов
```batch
docker-compose logs -f telegram-bot
```

### Остановка бота
```batch
docker-compose down
```

### Перезапуск с пересборкой
```batch
docker-compose up --build
```

### Статус контейнера
```batch
docker-compose ps
```

## 📊 Мониторинг

### Просмотр ресурсов
```batch
docker stats meeting-telegram-bot
```

### Логи в реальном времени
```batch
docker-compose logs -f
```

### Вход в контейнер для отладки
```batch
docker-compose exec telegram-bot /bin/bash
```

## ⚙️ Конфигурация

### Переменные окружения (.env)

| Переменная | Описание | Обязательно |
|-----------|----------|------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | ✅ |
| `DEEPGRAM_API_KEY` | API ключ Deepgram | ✅ |
| `CLAUDE_API_KEY` | API ключ Claude | ✅ |
| `LOG_LEVEL` | Уровень логирования | ❌ |
| `MAX_FILE_SIZE_MB` | Макс. размер файла | ❌ |

### Docker Compose настройки

Основные параметры в `docker-compose.yml`:

```yaml
# Монтирование конфигурационных файлов
volumes:
  # Конфигурационные файлы (только чтение)
  - ./bot_config.json:/app/bot_config.json:ro
  - ./config.json:/app/config.json:ro
  - ./templates_config.json:/app/templates_config.json:ro
  - ./names_config.json:/app/names_config.json:ro
  - ./team_config.json:/app/team_config.json:ro
  
  # Рабочие директории
  - ./logs:/app/logs
  - ./temp_files:/app/temp_bot_files
  - ./output:/app/meeting_output

# Ограничения ресурсов
deploy:
  resources:
    limits:
      memory: 2G      # Максимум памяти
      cpus: '1.0'     # Максимум CPU
    reservations:
      memory: 512M    # Гарантированная память
      cpus: '0.25'    # Гарантированный CPU
```

### Конфигурация бота (bot_config.json)

```json
{
  "telegram": {
    "allowed_users": [],           // Разрешенные пользователи (пусто = все)
    "admin_users": [123456789],    // ID администраторов
    "max_file_size_mb": 100        // Максимальный размер файла
  },
  "processing": {
    "default_template": "standard", // Шаблон по умолчанию
    "max_concurrent_jobs": 3,       // Максимум одновременных задач
    "processing_timeout": 1800      // Таймаут обработки (сек)
  }
}
```

## 🔧 Устранение неисправностей

### Проблема: Docker Desktop не запускается

**Решение:**
1. Убедитесь, что виртуализация включена в BIOS
2. Включите Hyper-V в Windows Features
3. Перезагрузите компьютер
4. Запустите Docker Desktop от имени администратора

### Проблема: Ошибка "Cannot connect to Docker daemon"

**Решение:**
```batch
# Проверьте статус Docker
docker info

# Перезапустите Docker Desktop
# Через GUI или из командной строки:
net stop com.docker.service
net start com.docker.service
```

### Проблема: Бот не отвечает на команды

**Проверка:**
```batch
# Просмотрите логи
docker-compose logs telegram-bot

# Проверьте переменные окружения
docker-compose exec telegram-bot env | grep TOKEN

# Проверьте статус контейнера
docker-compose ps
```

### Проблема: Ошибки конфигурационных файлов

**Решение:**
1. Проверьте JSON синтаксис в конфигурационных файлах
2. Убедитесь, что все файлы существуют в корневой папке:
   - `bot_config.json`
   - `config.json`
   - `templates_config.json`
   - `names_config.json`
   - `team_config.json`

3. Пересоздайте файлы через `setup_bot.bat`

### Проблема: Ошибки API ключей

**Решение:**
1. Проверьте файл `.env`
2. Убедитесь, что API ключи действительны
3. Перезапустите контейнер:
```batch
docker-compose restart telegram-bot
```

### Проблема: Недостаточно места на диске

**Очистка:**
```batch
# Очистка неиспользуемых образов
docker system prune -a

# Очистка volumes
docker volume prune

# Очистка всего
docker system prune -a --volumes
```

### Проблема: Медленная обработка файлов

**Оптимизация:**
1. Увеличьте лимиты памяти в `docker-compose.yml`
2. Используйте SSD диск для Docker volumes
3. Настройте параллельную обработку в `bot_config.json`:
```json
{
  "processing": {
    "max_concurrent_jobs": 5,
    "chunk_duration_minutes": 10
  }
}
```

## 🔐 Безопасность

### Защита API ключей

1. **Никогда не коммитьте конфигурационные файлы в Git**
```gitignore
# Добавьте в .gitignore
.env
.env.*
bot_config.json
config.json
templates_config.json
names_config.json
team_config.json
logs/
temp_files/
output/
```

2. **Используйте Docker Secrets для продакшена**
```yaml
secrets:
  telegram_token:
    external: true
  deepgram_key:
    external: true
```

3. **Ограничьте доступ к файлам**
```batch
# Установите права только для владельца
icacls *.json /grant:r %USERNAME%:F /inheritance:r
icacls .env /grant:r %USERNAME%:F /inheritance:r
```

### Сетевая безопасность

Бот изолирован в собственной Docker сети `meeting-bot-network`.

### Мониторинг доступа

Логи сохраняются в `# 🐳 Meeting Telegram Bot - Docker Setup

## 🚀 Быстрый старт

### 1. Предварительные требования

- **Windows 10/11** с включенной виртуализацией
- **Docker Desktop** - [скачать здесь](https://www.docker.com/products/docker-desktop/)
- **Git** (опционально) - для клонирования репозитория

### 2. Установка Docker Desktop

1. Скачайте Docker Desktop с официального сайта
2. Запустите установщик и следуйте инструкциям
3. После установки перезагрузите компьютер
4. Запустите Docker Desktop и дождитесь полной загрузки

### 3. Первоначальная настройка

```batch
# Запустите скрипт первоначальной настройки
setup_bot.bat
```

Скрипт автоматически:
- Проверит наличие Docker Desktop
- Создаст необходимые директории
- Создаст конфигурационные файлы
- Поможет настроить API ключи
- Соберет Docker образ

### 4. Настройка API ключей

Отредактируйте файл `.env`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
```

### 5. Запуск бота

```batch
# Запустите интерактивный скрипт управления
run_bot.bat
```

## 📁 Структура проекта

```
meeting-bot/
├── 🐳 Docker файлы
│   ├── Dockerfile              # Конфигурация Docker образа
│   ├── docker-compose.yml      # Docker Compose конфигурация
│   ├── requirements.txt        # Python зависимости
│   └── .dockerignore           # Исключения для Docker
│
├── ⚙️ Конфигурация
│   ├── .env                    # Переменные окружения (создается автоматически)
│   ├── .env.example            # Пример файла окружения
│   └── config/                 # Конфигурационные файлы
│       ├── bot_config.json     # Настройки бота
│       └── config.json         # Основная конфигурация
│
├── 📝 Python код
│   ├── telegram_bot.py         # Основной файл бота
│   ├── meeting_processor.py    # Обработчик встреч
│   └── *.py                    # Другие модули
│
├── 🗂️ Рабочие директории
│   ├── logs/                   # Логи (монтируется в контейнер)
│   ├── temp_files/             # Временные файлы
│   └── output/                 # Результаты обработки
│
└── 🛠️ Windows скрипты
    ├── setup_bot.bat           # Первоначальная настройка
    └── run_bot.bat             # Управление ботом
```

## 🎛️ Управление ботом

### Запуск в фоне
```batch
docker-compose up -d
```

### Просмотр логов
```batch
docker-compose logs -f telegram-bot
```

### Остановка бота
```batch
docker-compose down
```

### Перезапуск с пересборкой
```batch
docker-compose up --build
```

### Статус контейнера
```batch
docker-compose ps
```

## 📊 Мониторинг

### Просмотр ресурсов
```batch
docker stats meeting-telegram-bot
```

### Логи в реальном времени
```batch
docker-compose logs -f
```

### Вход в контейнер для отладки
```batch
docker-compose exec telegram-bot /bin/bash
```

## ⚙️ Конфигурация

### Переменные окружения (.env)

| Переменная | Описание | Обязательно |
|-----------|----------|------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | ✅ |
| `DEEPGRAM_API_KEY` | API ключ Deepgram | ✅ |
| `CLAUDE_API_KEY` | API ключ Claude | ✅ |
| `LOG_LEVEL` | Уровень логирования | ❌ |
| `MAX_FILE_SIZE_MB` | Макс. размер файла | ❌ |

### Docker Compose настройки

Основные параметры в `docker-compose.yml`:

```yaml
# Ограничения ресурсов
deploy:
  resources:
    limits:
      memory: 2G      # Максимум памяти
      cpus: '1.0'     # Максимум CPU
    reservations:
      memory: 512M    # Гарантированная память
      cpus: '0.25'    # Гарантированный CPU
```

### Конфигурация бота (config/bot_config.json)

```json
{
  "telegram": {
    "allowed_users": [],           // Разрешенные пользователи (пусто = все)
    "admin_users": [123456789],    // ID администраторов
    "max_file_size_mb": 100        // Максимальный размер файла
  },
  "processing": {
    "default_template": "standard", // Шаблон по умолчанию
    "max_concurrent_jobs": 3,       // Максимум одновременных задач
    "processing_timeout": 1800      // Таймаут обработки (сек)
  }
}
```

## 🔧 Устранение неисправностей

### Проблема: Docker Desktop не запускается

**Решение:**
1. Убедитесь, что виртуализация включена в BIOS
2. Включите Hyper-V в Windows Features
3. Перезагрузите компьютер
4. Запустите Docker Desktop от имени администратора

### Проблема: Ошибка "Cannot connect to Docker daemon"

**Решение:**
```batch
# Проверьте статус Docker
docker info

# Перезапустите Docker Desktop
# Через GUI или из командной строки:
net stop com.docker.service
net start com.docker.service
```

### Проблема: Бот не отвечает на команды

**Проверка:**
```batch
# Просмотрите логи
docker-compose logs telegram-bot

# Проверьте переменные окружения
docker-compose exec telegram-bot env | grep TOKEN

# Проверьте статус контейнера
docker-compose ps
```

### Проблема: Ошибки API ключей

**Решение:**
1. Проверьте файл `.env`
2. Убедитесь, что API ключи действительны
3. Перезапустите контейнер:
```batch
docker-compose restart telegram-bot
```

### Проблема: Недостаточно места на диске

**Очистка:**
```batch
# Очистка неиспользуемых образов
docker system prune -a

# Очистка volumes
docker volume prune

# Очистка всего
docker system prune -a --volumes
```

### Проблема: Медленная обработка файлов

**Оптимизация:**
1. Увеличьте лимиты памяти в `docker-compose.yml`
2. Используйте SSD диск для Docker volumes
3. Настройте параллельную обработку в конфигурации

## 🔐 Безопасность

### Защита API ключей

1. **Никогда не коммитьте .env файл в Git**
```gitignore
# Добавьте в .gitignore
.env
.env.*
```

2. **Используйте Docker Secrets для продакшена**
```yaml
secrets:
  telegram_token:
    external: true
  deepgram_key:
    external: true
```

3. **Ограничьте доступ к файлам**
```batch
# Установите права только для владельца
icacls .env /grant:r %USERNAME%:F /inheritance:r
```

### Сетевая безопасность

Бот изолирован в собственной Docker сети `meeting-bot-network`.

### Мониторинг доступа

Логи сохраняются в `logs/telegram_bot.log` и содержат информацию о:
- Попытках доступа
- Обработанных файлах
- Ошибках API

## 📈 Мониторинг и логирование

### Структура логов

```
logs/
├── telegram_bot.log      # Основные логи бота
├── telegram_bot.log.1    # Ротированные логи
└── ...
```

### Настройка логирования

В `config/bot_config.json`:
```json
{
  "logging": {
    "log_level": "INFO",           // DEBUG, INFO, WARNING, ERROR
    "log_file": "telegram_bot.log",
    "max_log_size_mb": 100,        // Размер до ротации
    "log_user_activity": true      // Логировать действия пользователей
  }
}
```

### Мониторинг в реальном времени

```batch
# Логи в реальном времени
docker-compose logs -f telegram-bot

# Только ошибки
docker-compose logs telegram-bot | findstr "ERROR"

# Статистика использования
docker stats meeting-telegram-bot --no-stream
```

## 🚀 Продвинутое использование

### Webhook режим

Для продакшена рекомендуется использовать webhook:

1. Настройте домен и SSL сертификат
2. Обновите `config/bot_config.json`:
```json
{
  "telegram": {
    "webhook_url": "https://yourdomain.com/webhook",
    "webhook_port": 8443
  }
}
```

3. Обновите `docker-compose.yml`:
```yaml
ports:
  - "443:8443"  # HTTPS порт
```

### Автозапуск

Настройте автозапуск Docker контейнера:

```yaml
# В docker-compose.yml
services:
  telegram-bot:
    restart: unless-stopped  # Автоперезапуск
```

### Резервное копирование

Создайте скрипт для бэкапа:

```batch
@echo off
set BACKUP_DIR=backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%
mkdir %BACKUP_DIR%
xcopy config %BACKUP_DIR%\config\ /E /I
xcopy logs %BACKUP_DIR%\logs\ /E /I
echo Backup created: %BACKUP_DIR%
```

### Масштабирование

Для высоких нагрузок:

```yaml
# docker-compose.yml
services:
  telegram-bot:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

## 📞 Поддержка

### Диагностика

Запустите полную диагностику:

```batch
# Проверка Docker
docker --version
docker info

# Проверка контейнера
docker-compose ps
docker-compose logs --tail=50 telegram-bot

# Проверка конфигурации
type .env
type config\bot_config.json
```

### Получение помощи

1. **Проверьте логи** - большинство проблем видны в логах
2. **Проверьте конфигурацию** - убедитесь в правильности API ключей
3. **Перезапустите сервисы** - иногда помогает простой перезапуск

### Полная переустановка

Если что-то пошло не так:

```batch
# Остановка и удаление
docker-compose down --rmi all --volumes

# Очистка системы
docker system prune -a --volumes

# Повторная настройка
setup_bot.bat
```

## ✨ Дополнительные возможности

### Плагины и расширения

Добавьте собственные модули в контейнер:

```dockerfile
# В Dockerfile
COPY plugins/ /app/plugins/
```

### Интеграция с внешними сервисами

Настройте дополнительные сервисы в `docker-compose.yml`:

```yaml
services:
  telegram-bot:
    # ... основная конфигурация
  
  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data
  
  database:
    image: postgres:13
    environment:
      POSTGRES_DB: meetingbot
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  redis_data:
  db_data:
```

---

🎉 **Готово!** Ваш Meeting Telegram Bot готов к работе в Docker контейнере!