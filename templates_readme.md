# 📝 Система шаблонов протоколов встреч

Система шаблонов позволяет создавать разные типы протоколов в зависимости от характера встречи.

## 🏗️ Структура файлов

```
meeting_templates.py      # Основной класс с шаблонами
templates_config.json     # Конфигурация шаблонов
template_manager.py       # Утилита управления шаблонами
config.json              # Обновленная основная конфигурация
```

## 📋 Встроенные шаблоны

| Шаблон | Описание | Когда использовать |
|--------|----------|-------------------|
| `standard` | Универсальный протокол | Обычные встречи |
| `business` | Официальный деловой протокол | Деловые встречи, переговоры |
| `project` | Фокус на управлении проектом | Проектные встречи, планирование |
| `standup` | Краткий формат для стендапов | Daily standup, короткие созвоны |
| `interview` | Структурированный отчет | Собеседования, интервью |
| `brainstorm` | Организация идей | Мозговые штурмы, креативные сессии |
| `review` | Ретроспективы и анализ | Ретроспективы, обзоры проектов |
| `planning` | Стратегическое планирование | Планирование, постановка целей |
| `technical` | Технические обсуждения | Архитектурные решения, код-ревью |
| `sales` | Встречи по продажам | Продажи, работа с клиентами |

## 🚀 Использование

### Через командную строку

```bash
# Стандартный шаблон
python meeting_processor.py meeting.mp4

# Конкретный шаблон
python meeting_processor.py meeting.mp4 --template business

# Автоопределение типа встречи
python meeting_processor.py meeting.mp4 --template auto

# Показать доступные шаблоны
python meeting_processor.py --list-templates
```

### В конфигурации

```json
{
  "settings": {
    "template_type": "business"
  }
}
```

## 🛠️ Управление шаблонами

### Менеджер шаблонов
```bash
python template_manager.py
```

Функции менеджера:
- 📋 Просмотр доступных шаблонов
- 📖 Превью шаблонов
- ✨ Создание пользовательских шаблонов  
- 🤖 Тест автоопределения типа
- 📤📥 Экспорт/импорт шаблонов

### Создание пользовательского шаблона

```python
templates = MeetingTemplates()
custom_template = """
Проанализируй транскрипт и создай краткий отчет:
{datetime_info}
Транскрипт: {transcript}

Создай отчет:
1. Участники
2. Основные темы  
3. Решения
"""
templates.add_custom_template("my_template", custom_template)
```

## 🤖 Автоопределение типа встречи

Система анализирует ключевые слова в транскрипте:

- **Standup**: "вчера", "сегодня", "блокеры", "планы"
- **Project**: "проект", "задача", "дедлайн", "milestone"  
- **Business**: "бюджет", "ROI", "стратегия", "клиент"
- **Technical**: "код", "архитектура", "баг", "API"
- **Sales**: "продажа", "сделка", "лид", "конверсия"

```bash
python meeting_processor.py meeting.mp4 --template auto
```

## ⚙️ Конфигурация шаблонов

В `templates_config.json`:

```json
{
  "default_template": "standard",
  "template_settings": {
    "include_technical_info": true,
    "include_file_datetime": true,
    "max_tokens": 2000,
    "auto_detect_meeting_type": false
  },
  "custom_templates": {
    "my_template": "Ваш пользовательский шаблон..."
  }
}
```

## 📝 Переменные шаблонов

В шаблонах доступны переменные:

- `{datetime_info}` - информация о дате и времени
- `{datetime_display}` - отформатированная дата
- `{transcript}` - транскрипт встречи

## 🔄 Миграция с предыдущих версий

Старые файлы будут работать без изменений. Новые возможности:

1. Добавьте в `config.json`:
```json
{
  "settings": {
    "template_type": "standard"
  },
  "paths": {
    "templates_config": "templates_config.json"
  }
}
```

2. Файлы `meeting_templates.py` и `templates_config.json` создадутся автоматически.

## 💡 Примеры использования

### Для разработчиков
```bash
python meeting_processor.py standup.mp3 --template standup
```

### Для бизнеса
```bash
python meeting_processor.py negotiation.mp4 --template business
```

### Для интервью
```bash
python meeting_processor.py interview.mp3 --template interview
```

### Автоматическое определение
```bash
python meeting_processor.py unknown_meeting.mp4 --template auto
```

## 🆘 Поддержка

Если шаблонная система недоступна, используется встроенный стандартный шаблон для обратной совместимости.
