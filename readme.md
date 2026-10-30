# Процессор видео встреч

Скрипт для автоматической обработки видеозаписей встреч: извлечение аудио, транскрипция и создание протокола встречи.

## Установка

1. Установите Python зависимости:
```bash
pip install -r requirements.txt
```

2. Установите ffmpeg для извлечения аудио:
```bash
# Автоматическая установка
python install_ffmpeg.py

# Или вручную:
# Windows: скачайте с https://ffmpeg.org/download.html
# macOS: brew install ffmpeg  
# Linux: sudo apt install ffmpeg
```

3. Получите API ключи:
   - **Deepgram**: зарегистрируйтесь на [deepgram.com](https://deepgram.com) и получите API ключ
   - **OpenRouter**: получите ключ на [openrouter.ai](https://openrouter.ai) для доступа к моделям Claude

## Настройка

### 1. Основная конфигурация (config.json)

Отредактируйте файл `config.json`:

```json
{
  "paths": {
    "input_file": "path/to/your/meeting.mp4",
    "output_dir": "meeting_output"
  },
  "settings": {
    "keep_audio_file": false,
    "language": "ru",
    "deepgram_model": "nova-2"
  }
}
```

### 2. Конфигурация токенов доступа

Установите переменные окружения:

```bash
export DEEPGRAM_API_KEY="ваш_ключ_deepgram"
export CLAUDE_API_KEY="ваш_ключ_openrouter"
```

Или создайте файл `.env`:

```bash
DEEPGRAM_API_KEY=ваш_ключ_deepgram
CLAUDE_API_KEY=ваш_ключ_openrouter
```

## Использование

### 1. Командная строка (рекомендуется)

```bash
# Простое использование
python meeting_processor.py meeting.mp4

# С дополнительными параметрами
python meeting_processor.py audio.mp3 --output results --timeout 600

# Все доступные опции
python meeting_processor.py file.ogg \
    --output output_dir \
    --timeout 300 \
    --chunks 5 \
    --config my_config.json \
    --keep-audio
```

### 2. Удобные скрипты

**Linux/macOS:**
```bash
chmod +x process_meeting.sh
./process_meeting.sh meeting.mp4
./process_meeting.sh audio.mp3 --timeout 600
```

**Windows:**
```cmd
process_meeting.bat meeting.mp4
process_meeting.bat audio.mp3 --timeout 600
```

### 3. Конфигурационный файл

Отредактируйте `config.json` и запустите без аргументов:
```bash
python meeting_processor.py
```

### 4. Аргументы командной строки

| Аргумент | Описание | Пример |
|----------|----------|---------|
| `input_file` | Путь к файлу | `meeting.mp4` |
| `-o, --output` | Выходная директория | `--output results` |
| `-t, --timeout` | Таймаут Deepgram (сек) | `--timeout 600` |
| `-c, --config` | Файл конфигурации | `--config my.json` |
| `--chunks` | Размер частей (мин) | `--chunks 5` |
| `--keep-audio` | Сохранить аудио | `--keep-audio` |
| `--claude-model` | Модель Claude | `--claude-model claude-3-opus-20240229` |
| `-h, --help` | Справка | `--help` |

### 5. Выбор модели Claude

```bash
# Интерактивный выбор модели
python select_claude_model.py

# Прямое указание модели
python meeting_processor.py file.mp3 --claude-model claude-3-opus-20240229
```

**Доступные модели Claude через OpenRouter:**

| Модель | Скорость | Качество | Стоимость | Лучше всего для |
|--------|----------|----------|-----------|----------------|
| Claude 3 Haiku | ⚡⚡⚡ | ⭐⭐⭐ | 💰 | Быстрая обработка |
| Claude 3 Sonnet | ⚡⚡ | ⭐⭐⭐⭐ | 💰💰 | Обычные встречи (рекомендуется) |
| Claude 3 Opus | ⚡ | ⭐⭐⭐⭐⭐ | 💰💰💰 | Важные встречи |
| Claude Sonnet 4 | ⚡⚡ | ⭐⭐⭐⭐⭐ | 💰💰💰 | Новейшие возможности |

> 🔄 **Важно**: Система теперь использует OpenRouter API для доступа к моделям Claude. Это обеспечивает более стабильный доступ и дополнительные возможности.

## Результаты

Скрипт создаст в выходной папке:

- `meeting_transcript.txt` - полный транскрипт встречи
- `meeting_summary.md` - **структурированный протокол встречи в формате Markdown**, включающий:
  - Краткое резюме встречи
  - Основные обсуждаемые вопросы
  - Принятые решения
  - Назначенные задачи и ответственные
  - Следующие шаги
  - Дата следующей встречи (если упоминалась)

> 📖 **Подробное руководство по просмотру результатов**: [`markdown_viewing_guide.md`](markdown_viewing_guide.md)

## Структура файлов

```
├── meeting_processor.py     # Основной скрипт
├── config.json             # Основные настройки
├── requirements.txt        # Зависимости Python
├── README.md              # Эта инструкция
└── meeting_output/        # Папка с результатами (создается автоматически)
    ├── meeting_transcript.txt
    └── meeting_summary.md
```

## Поддерживаемые форматы

### 📹 **Видеофайлы:**
- MP4, AVI, MOV, MKV, WMV, WebM
- *Извлечение аудиодорожки через ffmpeg*

### 🎵 **Аудиофайлы (нативная поддержка Deepgram):**
- **MP3, WAV, FLAC, AAC, M4A, OGG** ⚡
- *Отправляются напрямую в Deepgram без конвертации*

### 🔄 **Аудиофайлы (требуют конвертации):**
- WMA, OPUS
- *Конвертируются в WAV перед отправкой*

**Преимущества нативной поддержки:**
- ✅ **Быстрее** - нет времени на конвертацию
- ✅ **Качественнее** - без потери качества при перекодировании  
- ✅ **Экономичнее** - меньше использования диска
- ✅ **Надежнее** - меньше точек отказа

## Возможные проблемы

1. **Ошибка при извлечении аудио**: убедитесь, что установлен moviepy и видеофайл не поврежден
2. **Ошибка транскрипции**: проверьте API ключ Deepgram и наличие интернет-соединения

## Примечания

- Временный аудиофайл автоматически удаляется после обработки
- Все результаты сохраняются в кодировке UTF-8 для корректного отображения русского текста
- Скрипт поддерживает автоматическое разделение речи по спикерам
