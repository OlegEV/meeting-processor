# Деплой Meeting Processor

## Описание

Этот проект включает два независимых сервиса:
- **Веб-интерфейс** - Flask приложение для загрузки и обработки файлов через браузер
- **Telegram бот** - бот для обработки файлов через Telegram

**Важно**: Сервисы полностью независимы друг от друга и могут запускаться отдельно. Telegram бот не зависит от веб-интерфейса и наоборот.

**Технические особенности**:
- Базовый образ: `python:3.11-alpine` (компактный и безопасный)
- Размер образов: ~200-300 МБ (вместо ~1 ГБ на Debian)
- Общая папка логов `logs/` для централизованного логирования
- Retry логика для Deepgram API с экспоненциальной задержкой

## Структура логов

```
logs/
├── web_app.log          # Логи веб-сервиса
├── telegram_bot.log     # Логи Telegram бота
├── web_app.log.1        # Ротированные логи веб-сервиса
└── telegram_bot.log.1   # Ротированные логи бота
```

## Быстрый старт с Docker Compose

### 1. Подготовка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd meeting-processor

# Создайте файл переменных окружения
cp .env.example .env

# Отредактируйте .env файл
nano .env
```

### 2. Настройка переменных окружения

Заполните файл `.env`:

```bash
# API ключи
DEEPGRAM_API_KEY=your_deepgram_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here

# Telegram бот
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Настройки Flask
FLASK_ENV=production
FLASK_DEBUG=false
```

### 3. Запуск сервисов

```bash
# Создание и запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f meeting-web
docker-compose logs -f meeting-bot
```

### 4. Проверка работы

```bash
# Проверка статуса сервисов
docker-compose ps

# Проверка health check веб-сервиса
curl http://localhost:5000/health

# Просмотр логов в реальном времени
tail -f logs/web_app.log
tail -f logs/telegram_bot.log
```

**Примечание**: Веб-сервис доступен на порту 5000 (внешний), но внутри контейнера работает на порту 8000.

## Управление сервисами

### Остановка сервисов
```bash
docker-compose down
```

### Перезапуск сервисов
```bash
docker-compose restart
```

### Обновление сервисов
```bash
# Пересборка и перезапуск
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Просмотр логов
```bash
# Все логи
docker-compose logs

# Логи с отслеживанием
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs meeting-web
docker-compose logs meeting-bot

# Последние N строк
docker-compose logs --tail=100 meeting-web
```

### Запуск отдельных сервисов

Поскольку сервисы независимы, их можно запускать по отдельности:

```bash
# Запуск только веб-сервиса
docker-compose up -d meeting-web

# Запуск только Telegram бота
docker-compose up -d meeting-bot

# Остановка конкретного сервиса
docker-compose stop meeting-web
docker-compose stop meeting-bot

# Перезапуск конкретного сервиса
docker-compose restart meeting-web
docker-compose restart meeting-bot
```

## Мониторинг

### Health Check
Веб-сервис предоставляет endpoint для проверки здоровья:
```bash
curl http://localhost:5000/health
```

Ответ:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-05T10:22:00.000Z",
  "version": "1.0.0",
  "active_jobs": 0
}
```

### Логи
Все логи сохраняются в папке `logs/` с ротацией:
- Максимальный размер файла: 100 МБ
- Количество backup файлов: 3
- Кодировка: UTF-8

## Конфигурация

### Файлы конфигурации
- `config.json` - основная конфигурация веб-сервиса
- `bot_config.json` - конфигурация Telegram бота
- `api_keys.json` - API ключи (альтернатива переменным окружения)
- `templates_config.json` - настройки шаблонов
- `team_config.json` - настройки команды

### Volumes
```yaml
volumes:
  - ./logs:/app/logs                    # Общие логи
  - ./web_uploads:/app/web_uploads      # Загрузки веб-сервиса
  - ./web_output:/app/web_output        # Результаты веб-сервиса
  - ./temp_bot_files:/app/temp_bot_files # Временные файлы бота
  - ./meeting_output:/app/meeting_output # Результаты бота
```

## Troubleshooting

### Проблемы с запуском

1. **Проверьте переменные окружения**:
   ```bash
   docker-compose config
   ```

2. **Проверьте логи**:
   ```bash
   docker-compose logs meeting-web
   docker-compose logs meeting-bot
   ```

3. **Проверьте файлы конфигурации**:
   ```bash
   ls -la *.json
   ```

### Проблемы с API ключами

1. **Проверьте .env файл**:
   ```bash
   cat .env
   ```

2. **Проверьте переменные в контейнере**:
   ```bash
   docker-compose exec meeting-web env | grep API
   docker-compose exec meeting-bot env | grep API
   ```

### Проблемы с логами

1. **Проверьте права доступа**:
   ```bash
   ls -la logs/
   ```

2. **Создайте папку логов вручную**:
   ```bash
   mkdir -p logs
   chmod 755 logs
   ```

### Проблемы с сетью

1. **Проверьте порты**:
   ```bash
   netstat -tlnp | grep 5000
   ```

2. **Проверьте Docker сеть**:
   ```bash
   docker network ls
   docker network inspect meeting-processor_meeting-network
   ```

## Масштабирование

### Увеличение ресурсов
Отредактируйте `docker-compose.yml`:

```yaml
services:
  meeting-web:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### Несколько экземпляров веб-сервиса
```yaml
services:
  meeting-web:
    scale: 3
    ports:
      - "5000-5002:5000"
```

## Backup

### Backup логов
```bash
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

### Backup конфигурации
```bash
tar -czf config-backup-$(date +%Y%m%d).tar.gz *.json .env
```

## Преимущества Alpine Linux

### Размер образов
- **Alpine**: ~200-300 МБ на образ
- **Debian/Ubuntu**: ~800-1200 МБ на образ
- **Экономия**: до 70% места на диске

### Безопасность
- Минимальная поверхность атаки
- Регулярные обновления безопасности
- Отсутствие лишних пакетов

### Производительность
- Быстрая загрузка образов
- Меньшее потребление памяти
- Быстрый старт контейнеров

### Совместимость
- Все Python пакеты работают корректно
- FFmpeg и curl доступны через apk
- Полная совместимость с Docker Compose

## Обновления

### Обновление retry логики
Retry логика для Deepgram API уже включена:
- Максимум 3 попытки по умолчанию
- Экспоненциальная задержка между попытками
- Подробное логирование всех попыток

### Обновление логирования
Логирование унифицировано между сервисами:
- Общая папка `logs/`
- Ротация файлов
- Одинаковый формат логов
- UTF-8 кодировка

### Переход на Alpine Linux
Образы обновлены для использования Alpine Linux:
- Компактные образы (экономия ~70% места)
- Улучшенная безопасность
- Быстрый старт контейнеров
- Полная совместимость с существующим функционалом

## Поддержка

При возникновении проблем:
1. Проверьте логи в папке `logs/`
2. Убедитесь в корректности API ключей
3. Проверьте статус сервисов через `docker-compose ps`
4. Используйте health check endpoint для диагностики
