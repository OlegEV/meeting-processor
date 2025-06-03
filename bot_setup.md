# 🤖 Настройка Telegram бота для обработки встреч

## 📋 Требования

### Python пакеты
```bash
pip install python-telegram-bot
pip install deepgram-sdk
pip install anthropic
pip install requests
```

### Системные требования
- Python 3.8+
- FFmpeg (для обработки аудио/видео)
- Минимум 2GB RAM
- Достаточно места на диске для временных файлов

## 🚀 Быстрый старт

### 1. Создание Telegram бота

1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте команду `/newbot`
3. Введите имя бота (например: "Meeting Processor Bot")
4. Введите username бота (например: "meeting_processor_bot")
5. Скопируйте полученный токен

### 2. Настройка конфигурации

Отредактируйте файл `bot_config.json`:

```json
{
  "telegram": {
    "bot_token": "ВСТАВЬТЕ_ВАШ_ТОКЕН_СЮДА",
    "allowed_users": [123456789, 987654321],
    "admin_users": [123456789],
    "max_file_size_mb": 50
  }
}
```

**Как найти ID пользователя:**
- Отправьте `/start` боту [@userinfobot](https://t.me/userinfobot)
- Скопируйте ваш ID

### 3. Настройка API ключей

Отредактируйте файл `api_keys.json`:

```json
{
  "api_keys": {
    "deepgram": "ВАШ_DEEPGRAM_КЛЮЧ",
    "claude": "ВАШ_CLAUDE_КЛЮЧ"
  }
}
```

### 4. Запуск бота

```bash
python telegram_bot.py
```

## 🛠️ Детальная настройка

### Структура файлов
```
project/
├── telegram_bot.py          # Основной файл бота
├── bot_config.json          # Конфигурация бота
├── api_keys.json           # API ключи
├── meeting_processor.py    # Обработчик встреч
├── meeting_templates.py    # Шаблоны протоколов
├── templates_config.json   # Настройки шаблонов
├── names_config.json       # Замена имен спикеров
└── config.json            # Общие настройки
```

### Конфигурация безопасности

В `bot_config.json`:

```json
{
  "telegram": {
    "allowed_users": [123456789],    // Разрешенные пользователи
    "admin_users": [123456789]       // Администраторы
  },
  "security": {
    "rate_limit_messages_per_minute": 10,
    "rate_limit_files_per_hour": 5,
    "block_suspicious_files": true
  }
}
```

**Если `allowed_users` пуст - доступ разрешен всем!**

### Настройка обработки

```json
{
  "processing": {
    "default_template": "standard",
    "max_concurrent_jobs": 3,
    "processing_timeout": 1800,
    "auto_detect_template": false
  }
}
```

### Уведомления

```json
{
  "notifications": {
    "send_progress_updates": true,
    "notify_on_completion": true,
    "notify_on_error": true
  }
}
```

## 🎯 Использование бота

### Команды пользователя

| Команда | Описание |
|---------|----------|
| `/start` | Начать работу с ботом |
| `/help` | Справка по командам |
| `/templates` | Выбрать шаблон протокола |
| `/settings` | Показать текущие настройки |
| `/status` | Статус обработки файлов |
| `/cancel` | Отменить текущую обработку |

### Рабочий процесс

1. **Выбор шаблона:** `/templates` → выбрать подходящий шаблон
2. **Отправка файла:** Прикрепить аудио/видео файл
3. **Ожидание:** Бот обработает файл (2-15 минут)
4. **Результат:** Получить транскрипт и протокол

### Поддерживаемые форматы

**Аудио:** MP3, WAV, FLAC, AAC, M4A, OGG
**Видео:** MP4, AVI, MOV, MKV, WMV, WebM
**Размер:** До 50 МБ (настраивается)

## 🔧 Администрирование

### Команды администратора

```python
# В bot_config.json добавьте себя в admin_users
"admin_users": [ВАШ_ID]
```

Администраторы видят дополнительную статистику в `/settings`:
- Количество активных пользователей
- Файлов в обработке
- Системную информацию

### Мониторинг логов

```bash
tail -f telegram_bot.log
```

### Очистка временных файлов

```json
{
  "storage": {
    "temp_dir": "temp_bot_files",
    "keep_processed_files": false,
    "cleanup_interval_hours": 6
  }
}
```

## 🚨 Устранение неисправностей

### Проблема: Бот не отвечает
```bash
# Проверьте токен
grep "bot_token" bot_config.json

# Проверьте логи
tail telegram_bot.log
```

### Проблема: Ошибка API ключей
```bash
# Проверьте ключи
cat api_keys.json

# Тестируйте ключи отдельно
python -c "from meeting_processor import MeetingProcessor; print('OK')"
```

### Проблема: Файл не обрабатывается
1. Проверьте размер файла (макс. 50 МБ)
2. Проверьте формат файла
3. Проверьте наличие FFmpeg: `ffmpeg -version`
4. Проверьте место на диске

### Проблема: Нет доступа
1. Добавьте ваш ID в `allowed_users`
2. Перезапустите бота
3. Отправьте `/start`

## 🔒 Безопасность

### Защита API ключей
```bash
# Установите права доступа только для владельца
chmod 600 api_keys.json
chmod 600 bot_config.json

# Добавьте в .gitignore
echo "api_keys.json" >> .gitignore
echo "bot_config.json" >> .gitignore
```

### Ограничение доступа
```json
{
  "telegram": {
    "allowed_users": [123456789, 987654321]
  },
  "security": {
    "rate_limit_files_per_hour": 5
  }
}
```

## 🌐 Развертывание на сервере

### Systemd сервис

Создайте файл `/etc/systemd/system/meeting-bot.service`:

```ini
[Unit]
Description=Meeting Telegram Bot
After=network.target

[Service]
Type=simple
User=meetingbot
WorkingDirectory=/opt/meeting-bot
ExecStart=/usr/bin/python3 /opt/meeting-bot/telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable meeting-bot
sudo systemctl start meeting-bot
sudo systemctl status meeting-bot
```

### Docker

Создайте `Dockerfile`:

```dockerfile
FROM python:3.9-slim

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "telegram_bot.py"]
```

```bash
docker build -t meeting-bot .
docker run -d --name meeting-bot meeting-bot
```

### Webhook режим

В `bot_config.json`:

```json
{
  "telegram": {
    "webhook_url": "https://yourdomain.com/webhook",
    "webhook_port": 8443
  }
}
```

## 📊 Мониторинг

### Логирование

```json
{
  "logging": {
    "log_level": "INFO",
    "log_file": "telegram_bot.log",
    "log_file_processing": true
  }
}
```

### Метрики
- Количество обработанных файлов
- Время обработки
- Ошибки и их типы
- Активность пользователей

## 💡 Советы по использованию

### Для лучшего качества транскрипции:
- Используйте качественный микрофон
- Минимизируйте фоновый шум
- Говорите четко и не слишком быстро
- Файлы до 15 минут обрабатываются быстрее

### Выбор шаблона:
- `standup` - для ежедневных созвонов
- `business` - для официальных встреч
- `project` - для обсуждения проектов
- `interview` - для собеседований
- `auto` - автоматическое определение

### Оптимизация производительности:
- Установите `max_concurrent_jobs: 1` на слабых серверах
- Используйте SSD для временных файлов
- Регулярно очищайте логи

## 🆘 Поддержка

### Частые вопросы

**Q: Бот обрабатывает файл очень долго**
A: Проверьте размер файла и длительность. Файлы >15 минут разбиваются на части.

**Q: Качество транскрипции плохое**
A: Убедитесь в хорошем качестве аудио и отсутствии фонового шума.

**Q: Бот не создает протокол**
A: Проверьте API ключ Claude и лимиты использования.

### Получение помощи

1. Проверьте логи: `tail -f telegram_bot.log`
2. Проверьте конфигурацию: `python -c "import json; print(json.load(open('bot_config.json')))"`
3. Тестируйте модули отдельно: `python meeting_processor.py test.mp3`

### Обновление

```bash
git pull origin main
pip install -r requirements.txt --upgrade
sudo systemctl restart meeting-bot
```