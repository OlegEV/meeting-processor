---
plan_slug: admin-role
phase: implementation-plan
rig: meeting-processor
rig_root: /Users/egorovov/Documents/gc-spb/meeting-processor
artifact_root: /Users/egorovov/Documents/gc-spb/meeting-processor/plans
requirements_file: /Users/egorovov/Documents/gc-spb/meeting-processor/plans/admin-role/requirements.md
status: approved
created_at: 2026-06-14T18:15:00Z
updated_at: 2026-06-14T18:15:00Z
---

# Implementation Plan: Роль администратора

## Summary

Четыре файла меняются, один конфиг. Нет миграции БД, нет изменений JWT.
Все изменения обратно совместимы: при отсутствии `admin_user_ids` в конфиге
поведение системы не меняется.

## Current System

- `auth/decorators.py` — глобальный `_auth_decorators: AuthDecorators` хранит
  `self.config` после вызова `init_auth_decorators(token_validator, config)`.
  Функции `get_current_user_id()` / `is_authenticated()` уже экспортируются из
  `auth/user_context.py` и реэкспортируются через `auth/__init__.py`.

- `database/db_manager.py:910` — `get_all_jobs()` возвращает все задачи без
  JOIN с таблицей `users`; нет параметра `limit`.

- `database/db_manager.py:283` — `get_job_by_id(job_id, user_id=None)` уже
  поддерживает обход проверки owner при `user_id=None`.

- `run_web.py:414` — `get_job_status()` всегда передаёт `user_id` в
  `get_job_by_id`, запрещая доступ к чужим задачам.

- `run_web.py:1167` — `jobs_list()` вызывает `get_user_jobs(user_id, limit=50)`.

- `web_templates.py:749` — `get_jobs_template()` не имеет столбца
  «Пользователь»; вызывается без параметров.

## Proposed Implementation

### 1. `config.json` — добавить ключ `admin_user_ids`

В секцию `auth` добавить:
```json
"admin_user_ids": []
```
Читается как `config.get('auth', {}).get('admin_user_ids', [])`.

### 2. `auth/decorators.py` — добавить `is_current_user_admin()`

После инициализации `_auth_decorators` конфиг уже доступен.
Добавить публичную функцию в конец файла (после `create_auth_teardown`):

```python
def is_current_user_admin() -> bool:
    """Проверяет, является ли текущий пользователь администратором."""
    if _auth_decorators is None:
        return False
    admin_ids = _auth_decorators.config.get('auth', {}).get('admin_user_ids', [])
    if not admin_ids:
        return False
    from .user_context import get_current_user_id
    user_id = get_current_user_id()
    return user_id is not None and user_id in admin_ids
```

### 3. `auth/__init__.py` — реэкспортировать `is_current_user_admin`

Добавить в import из `.decorators` и в `__all__`:
```python
from .decorators import (
    ...
    is_current_user_admin,   # новое
)
```

### 4. `database/db_manager.py` — расширить `get_all_jobs()`

Заменить текущую реализацию на версию с JOIN пользователей и параметром `limit`:

```python
def get_all_jobs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Получает все задачи с базовой информацией о пользователях."""
    with self._get_connection() as conn:
        cursor = conn.cursor()
        sql = """
            SELECT j.*,
                   COALESCE(u.name, u.preferred_username, u.email, j.user_id) AS user_display
            FROM jobs j
            LEFT JOIN users u ON j.user_id = u.user_id
            ORDER BY j.created_at DESC
        """
        if limit:
            sql += f" LIMIT {limit}"
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
```

Поле `user_display` используется шаблоном; при отсутствии записи в `users`
откатывается к `user_id`.

### 5. `run_web.py` — три правки

**5a. Импорт** (строка 41, после `is_authenticated`):
```python
from auth import create_auth_system, require_auth, get_current_user_id, \
    get_current_user, is_authenticated, is_current_user_admin
```

**5b. `get_job_status()` (строка 414)** — пропустить фильтр owner для admin:
```python
def get_job_status(self, job_id: str) -> Optional[Dict]:
    try:
        user_id = get_current_user_id()
        if not user_id:
            logger.warning("Попытка получить статус задачи без аутентификации")
            return None

        if is_current_user_admin():
            logger.info(f"[ADMIN ACCESS] user_id={user_id} accessing job={job_id}")
            job_data = self.db_manager.get_job_by_id(job_id)   # без user_id
        else:
            job_data = self.db_manager.get_job_by_id(job_id, user_id)

        return job_data
    except Exception as e:
        logger.error(f"Ошибка получения статуса задачи {job_id}: {e}")
        return None
```

**5c. `jobs_list()` (строка 1167)** — ветвление по роли:
```python
@self.app.route('/jobs')
@require_auth()
def jobs_list():
    try:
        user_id = get_current_user_id()
        if not user_id:
            flash('Ошибка аутентификации', 'error')
            return redirect(url_for('index'))

        admin = is_current_user_admin()

        if admin:
            raw_jobs = self.db_manager.get_all_jobs(limit=100)
        else:
            raw_jobs = self.db_manager.get_user_jobs(user_id, limit=50)

        jobs = []
        for job_data in raw_jobs:
            created_at = job_data.get('created_at')
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = datetime.utcnow()
            elif not isinstance(created_at, datetime):
                created_at = datetime.utcnow()

            entry = {
                'id': job_data['job_id'],
                'filename': job_data['filename'],
                'status': job_data['status'],
                'template': job_data['template'],
                'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'progress': job_data.get('progress', 0),
            }
            if admin:
                entry['user_display'] = job_data.get('user_display', job_data['user_id'])
            jobs.append(entry)

        return render_template_string(
            self.templates.get_jobs_template(),
            jobs=jobs,
            is_admin=admin,
        )
    except Exception as e:
        logger.error(f"Ошибка получения списка задач: {e}")
        flash('Ошибка получения списка задач', 'error')
        return redirect(url_for('index'))
```

### 6. `web_templates.py` — столбец «Пользователь» в шаблоне

В `get_jobs_template()` (строка 749):

- Заголовок таблицы: добавить `<th>` сразу после `<th>Файл</th>`:
  ```html
  {% if is_admin %}<th>Пользователь</th>{% endif %}
  ```
- Строки тела: добавить `<td>` после `<td>{{ job.filename }}</td>`:
  ```html
  {% if is_admin %}<td><small class="text-muted">{{ job.user_display }}</small></td>{% endif %}
  ```
- Заголовок карточки: изменить текст в зависимости от роли:
  ```html
  <h4>{% if is_admin %}Все задачи (администратор){% else %}История обработки файлов{% endif %}</h4>
  ```

## Testing

- **Нет тестов для `jobs_list` и `get_job_status`** в `tests/` — покрытие через
  существующие Flask-тесты для маршрутов отсутствует. Верификация вручную:
  1. Запуск в `debug_mode=true` с `admin_user_ids: ["debug_user"]` → страница `/jobs`
     показывает все задачи + столбец «Пользователь».
  2. Без `debug_user` в `admin_user_ids` → обычное поведение.
  3. Попытка обычного пользователя открыть `/status/<чужой_job_id>` → 404/redirect.
  4. `get_all_jobs(limit=100)` возвращает не больше 100 строк.

- Добавить unit-тест для `is_current_user_admin()` в `tests/`:
  проверить, что функция возвращает `True` / `False` при разных конфигах и
  разных `user_id` в контексте.

## Rollout

1. Развернуть код.
2. В `config.json` добавить `auth.admin_user_ids` со своим `user_id`.
3. Перезапустить приложение (`python run_web.py` или `gunicorn`).
4. Открыть `/jobs` — убедиться в отображении всех задач и столбца «Пользователь».
5. Открыть `/status/<job_id_другого_пользователя>` — должен открыться.

## Open Questions

- Нет. Все решения выводятся из существующего кода.
