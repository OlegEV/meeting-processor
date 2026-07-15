---
plan_slug: admin-email
phase: tasks
rig: meeting-processor
rig_root: /Users/egorovov/Documents/gc-spb/meeting-processor
artifact_root: /Users/egorovov/Documents/gc-spb/meeting-processor/plans
requirements_file: /Users/egorovov/Documents/gc-spb/meeting-processor/plans/admin-email/requirements.md
implementation_plan_file: /Users/egorovov/Documents/gc-spb/meeting-processor/plans/admin-email/implementation-plan.md
status: created
created_at: '2026-06-15T00:00:00Z'
updated_at: '2026-06-15T20:02:19Z'
created_beads_at: '2026-06-15T20:02:19Z'
---

# Task Plan: Идентификация администратора по email

## Tasks

1. **config: admin_user_ids → admin_emails** — в `config.json` заменить ключ
2. **auth: обновить is_current_user_admin()** — читать `admin_emails`, сравнивать с `get_current_user_email()`
3. **test: обновить test_admin_role.py** — email в user_info, обновлённые assert'ы

## Bead Creation Payload

```yaml
target_rig: meeting-processor
convoys: []

beads:
  - key: config-admin-emails
    title: "config: заменить admin_user_ids на admin_emails"
    description: |
      В config.json в секции auth:
      - удалить "admin_user_ids": []
      - добавить "admin_emails": []
      Ключ читается через config.get('auth', {}).get('admin_emails', []).
    type: task
    priority: 2

  - key: auth-email-check
    title: "auth: обновить is_current_user_admin() на проверку по email"
    description: |
      В auth/decorators.py в функции is_current_user_admin() (строка 282):
      - admin_ids = ...get('admin_user_ids', []) → admin_emails = ...get('admin_emails', [])
      - current_user_id = UserContext.get_current_user_id() → current_email = UserContext.get_current_user_email()
      - return current_user_id is not None and current_user_id in admin_ids
        → return current_email is not None and current_email in admin_emails
      Также обновить docstring: упомянуть admin_emails и email вместо admin_user_ids и user_id.
    type: task
    priority: 2
    dependencies:
      - config-admin-emails

  - key: test-email-admin
    title: "test: обновить test_admin_role.py под проверку по email"
    description: |
      В tests/test_admin_role.py:
      - Переименовать тесты: admin_user_ids → admin_emails, user_id → email
      - В setUp/tearDown оставить без изменений
      - Во всех set_current_user добавить 'email': 'user@example.com' в user_info
      - Конфиг тестов: {'auth': {'admin_emails': [...]}} вместо {'auth': {'admin_user_ids': [...]}}
      - Тест True: email в admin_emails → True
      - Тест False: email не в admin_emails → False
      - Тест False: пустой admin_emails → False
      - Тест False: декораторы не инициализированы → False
    type: task
    priority: 3
    dependencies:
      - auth-email-check
```

## Created Beads

| Key | Kind | Bead ID | Title |
|---|---|---|---|
| config-admin-emails | bead | mp-1lz | config: заменить admin_user_ids на admin_emails |
| auth-email-check | bead | mp-2iv | auth: обновить is_current_user_admin() на проверку по email |
| test-email-admin | bead | mp-5bf | test: обновить test_admin_role.py под проверку по email |
