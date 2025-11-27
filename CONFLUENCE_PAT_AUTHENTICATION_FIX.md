# Исправление аутентификации Confluence Personal Access Token

## Проблема
Пользователь сообщил о необходимости использования Personal Access Token (PAT) вместо API токена для Confluence Server. Это объясняло ошибки 401 (аутентификация) и валидации данных публикации.

## Диагностика

### 1. Ошибка аутентификации (401)
- **Причина**: Confluence Server требует Bearer аутентификацию с Personal Access Token
- **Было**: Basic Auth с username:api_token
- **Стало**: Bearer токен для Server, Basic Auth для Cloud

### 2. Ошибка валидации данных публикации
- **Причина**: Неправильная структура данных в `run_web.py`
- **Было**: `page_id`, `page_url`, `space_key`, `status`
- **Стало**: `confluence_page_id`, `confluence_page_url`, `confluence_space_key`, `publication_status`

## Внесенные исправления

### 1. Обновление аутентификации в `confluence_client.py`

#### Добавлен метод определения типа Confluence:
```python
def _is_confluence_server(self) -> bool:
    """Определяет, является ли это Confluence Server (не Cloud)"""
    return '.atlassian.net' not in self.config.base_url.lower()
```

#### Обновлена инициализация клиента:
```python
def __init__(self, config: ConfluenceConfig):
    # Для Confluence Server используем Bearer токен (Personal Access Token)
    # Для Confluence Cloud используем Basic Auth (username:api_token)
    if self._is_confluence_server():
        # Personal Access Token для Confluence Server
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        logger.info("Используется Personal Access Token для Confluence Server")
    else:
        # Basic Auth для Confluence Cloud
        self.session.auth = (config.username, config.api_token)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        logger.info("Используется Basic Auth для Confluence Cloud")
```

#### Обновлена валидация конфигурации:
```python
def _validate_config(self):
    # Для Confluence Cloud требуется username, для Server - нет
    if not self._is_confluence_server() and not self.config.username:
        raise ConfluenceValidationError("Для Confluence Cloud требуется username")
```

### 2. Исправление структуры данных публикации в `run_web.py`

#### Успешная публикация (строки 957-966):
```python
publication_data = {
    'job_id': job_id,
    'confluence_page_id': page_info['id'],
    'confluence_page_url': page_url,
    'confluence_space_key': space_key,
    'page_title': page_title,
    'publication_status': 'published'
}
```

#### Ошибка публикации (строки 987-996):
```python
publication_data = {
    'job_id': job_id,
    'confluence_page_id': '',  # Пустой ID при ошибке
    'confluence_page_url': base_page_url,  # Используем исходный URL
    'confluence_space_key': space_key,
    'page_title': page_title,
    'publication_status': 'failed',
    'error_message': str(confluence_error)
}
```

## Схема валидации данных

Согласно `database/models.py` (строки 530-531), обязательные поля для публикации:
- `job_id` - ID задачи
- `confluence_page_id` - ID страницы в Confluence
- `confluence_page_url` - URL страницы в Confluence
- `confluence_space_key` - Ключ пространства
- `page_title` - Заголовок страницы

## Поддерживаемые форматы URL

Система теперь поддерживает все три формата Confluence URL:

1. **Confluence Cloud**: `https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Page+Title`
   - Аутентификация: Basic Auth (username:api_token)

2. **Confluence Server (pageId)**: `https://wiki.domain.com/pages/viewpage.action?pageId=123456`
   - Аутентификация: Bearer Personal Access Token

3. **Confluence Server (display)**: `https://wiki.domain.com/display/SPACE/PAGE`
   - Аутентификация: Bearer Personal Access Token

## Следующие шаги

Для завершения исправления необходимо:

1. **Обновить Personal Access Token в конфигурации**:
   - Заменить API токен в `config.json` на Personal Access Token
   - Убедиться, что токен имеет права на создание страниц в пространстве

2. **Протестировать публикацию**:
   - Запустить веб-приложение
   - Попробовать опубликовать протокол в Confluence
   - Проверить успешное создание страницы

## Технические детали

### Различия в аутентификации:
- **Confluence Cloud**: `Authorization: Basic base64(username:api_token)`
- **Confluence Server**: `Authorization: Bearer personal_access_token`

### Определение типа Confluence:
- Если URL содержит `.atlassian.net` → Confluence Cloud
- Иначе → Confluence Server

### Валидация данных:
- Все поля должны быть строками и не пустыми
- `publication_status` должен быть одним из: `published`, `failed`, `pending`, `retrying`
- `retry_count` должен быть неотрицательным числом

## Файлы изменены:
- `confluence_client.py` - обновлена аутентификация
- `run_web.py` - исправлена структура данных публикации
- `test_confluence_pat_fix.py` - создан тест для проверки исправлений