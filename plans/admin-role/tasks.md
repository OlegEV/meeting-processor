---
plan_slug: admin-role
phase: tasks
rig: meeting-processor
rig_root: /Users/egorovov/Documents/gc-spb/meeting-processor
artifact_root: /Users/egorovov/Documents/gc-spb/meeting-processor/plans
requirements_file: /Users/egorovov/Documents/gc-spb/meeting-processor/plans/admin-role/requirements.md
implementation_plan_file: /Users/egorovov/Documents/gc-spb/meeting-processor/plans/admin-role/implementation-plan.md
status: created
created_at: '2026-06-14T18:20:00Z'
updated_at: '2026-06-14T19:48:54Z'
created_beads_at: '2026-06-14T19:48:54Z'
---

# Task Plan: Роль администратора

## Tasks

1. **config: добавить admin_user_ids** — в `config.json` в секцию `auth` добавить `"admin_user_ids": []`
2. **auth: добавить is_current_user_admin()** — новая функция в `auth/decorators.py` + реэкспорт через `auth/__init__.py`
3. **db: расширить get_all_jobs()** — добавить `limit` и LEFT JOIN с `users` для поля `user_display`
4. **web: admin-доступ к задачам** — в `run_web.py`: импорт, `get_job_status()` без owner-фильтра для admin, `jobs_list()` с ветвлением
5. **templates: столбец Пользователь** — в `web_templates.py` добавить `{% if is_admin %}` столбец в таблицу задач
6. **test: unit-тест is_current_user_admin** — новый тест в `tests/`

## Bead Creation Payload

```yaml
target_rig: meeting-processor
convoys: []

beads:
  - key: config-admin-ids
    title: "config: добавить admin_user_ids в auth секцию"
    description: |
      В файле config.json добавить ключ "admin_user_ids": [] в секцию "auth".
      Чтение через dict.get('auth', {}).get('admin_user_ids', []) — совместимо
      со старыми конфигами без этого ключа.
    type: task
    priority: 2

  - key: auth-is-admin
    title: "auth: добавить функцию is_current_user_admin()"
    description: |
      В auth/decorators.py добавить публичную функцию is_current_user_admin(),
      которая читает admin_user_ids из _auth_decorators.config и сравнивает
      с get_current_user_id() из UserContext.
      В auth/__init__.py добавить is_current_user_admin в import и __all__.
    type: task
    priority: 2
    dependencies:
      - config-admin-ids

  - key: db-get-all-jobs
    title: "db: расширить get_all_jobs() — limit + user_display"
    description: |
      В database/db_manager.py изменить get_all_jobs():
      - добавить параметр limit: Optional[int] = None
      - добавить LEFT JOIN с users для поля user_display
        (COALESCE(u.name, u.preferred_username, u.email, j.user_id))
      Поле user_display используется шаблоном списка задач.
    type: task
    priority: 2

  - key: web-admin-access
    title: "web: admin-доступ в run_web.py"
    description: |
      В run_web.py три изменения:
      1. Импорт is_current_user_admin из auth (строка 41).
      2. get_job_status(): для admin вызывать get_job_by_id(job_id) без user_id
         и логировать [ADMIN ACCESS] user_id=... accessing job=...
      3. jobs_list(): при is_current_user_admin() вызывать get_all_jobs(limit=100),
         включать user_display в dict задачи, передавать is_admin=True в шаблон.
    type: task
    priority: 2
    dependencies:
      - auth-is-admin
      - db-get-all-jobs

  - key: templates-user-column
    title: "templates: столбец Пользователь в get_jobs_template()"
    description: |
      В web_templates.py в методе get_jobs_template() добавить:
      - В заголовок таблицы: {% if is_admin %}<th>Пользователь</th>{% endif %}
        после <th>Файл</th>
      - В строки тела: {% if is_admin %}<td><small>{{ job.user_display }}</small></td>{% endif %}
        после ячейки filename
      - Заголовок карточки: "Все задачи (администратор)" vs "История обработки файлов"
        через {% if is_admin %}
    type: task
    priority: 2
    dependencies:
      - web-admin-access

  - key: test-is-admin
    title: "test: unit-тест для is_current_user_admin()"
    description: |
      Добавить тест в tests/ (например, tests/test_admin_role.py):
      - is_current_user_admin() возвращает False при пустом admin_user_ids
      - возвращает True когда user_id текущего пользователя в списке
      - возвращает False когда user_id не в списке
      - возвращает False когда _auth_decorators не инициализированы
    type: task
    priority: 3
    dependencies:
      - auth-is-admin
```

## Created Beads

| Key | Kind | Bead ID | Title |
|---|---|---|---|
| config-admin-ids | bead | mp-j5f | config: добавить admin_user_ids в auth секцию |
| auth-is-admin | bead | mp-bax | auth: добавить функцию is_current_user_admin() |
| db-get-all-jobs | bead | mp-43q | db: расширить get_all_jobs() — limit + user_display |
| web-admin-access | bead | mp-iv2 | web: admin-доступ в run_web.py |
| templates-user-column | bead | mp-3rn | templates: столбец Пользователь в get_jobs_template() |
| test-is-admin | bead | mp-3rl | test: unit-тест для is_current_user_admin() |
