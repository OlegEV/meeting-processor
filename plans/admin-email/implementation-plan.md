---
plan_slug: admin-email
phase: implementation-plan
rig: meeting-processor
rig_root: /Users/egorovov/Documents/gc-spb/meeting-processor
artifact_root: /Users/egorovov/Documents/gc-spb/meeting-processor/plans
requirements_file: /Users/egorovov/Documents/gc-spb/meeting-processor/plans/admin-email/requirements.md
status: approved
created_at: 2026-06-15T00:00:00Z
updated_at: 2026-06-15T00:00:00Z
---

# Implementation Plan: Идентификация администратора по email

## Summary

Три файла меняются. Нет миграции БД, нет изменений JWT. Обратная совместимость
со старыми `config.json` без `admin_emails` обеспечивается через `.get(..., [])`.

## Current System

- `config.json:15` — `"admin_user_ids": []` в секции `auth`
- `auth/decorators.py:284` — `is_current_user_admin()` читает `admin_user_ids`
  и сравнивает с `UserContext.get_current_user_id()`
- `auth/user_context.py:54` — `UserContext.get_current_user_email()` уже
  существует и возвращает `user_info.get('email')` или `None`
- `tests/test_admin_role.py` — тесты используют `user_id` в `set_current_user`

## Proposed Implementation

### 1. `config.json` — переименовать ключ

Заменить `"admin_user_ids": []` на `"admin_emails": []` в секции `auth`.

### 2. `auth/decorators.py` — обновить `is_current_user_admin()`

```python
def is_current_user_admin() -> bool:
    """
    Проверяет, является ли текущий пользователь администратором.

    Читает admin_emails из конфигурации auth-системы и сравнивает
    с email текущего пользователя из UserContext.

    Returns:
        True если email текущего пользователя есть в списке admin_emails,
        иначе False. Возвращает False если декораторы не инициализированы
        или пользователь не аутентифицирован.
    """
    if _auth_decorators is None:
        return False
    admin_emails = _auth_decorators.config.get('auth', {}).get('admin_emails', [])
    if not admin_emails:
        return False
    current_email = UserContext.get_current_user_email()
    return current_email is not None and current_email in admin_emails
```

Изменения относительно текущего кода (строки 282–288):
- `admin_user_ids` → `admin_emails`
- `get_current_user_id()` → `get_current_user_email()`
- переменная `current_user_id` → `current_email`

### 3. `tests/test_admin_role.py` — обновить тесты

Все 4 теста используют `UserContext.set_current_user({'user_id': ...})`.
Добавить `email` в user_info, обновить логику проверок:

```python
def test_returns_false_when_admin_emails_empty(self):
    init_auth_decorators(None, {'auth': {'admin_emails': []}})
    UserContext.set_current_user({'user_id': 'user1', 'email': 'user1@example.com'})
    self.assertFalse(is_current_user_admin())

def test_returns_true_when_email_in_admin_emails(self):
    init_auth_decorators(None, {'auth': {'admin_emails': ['admin@example.com']}})
    UserContext.set_current_user({'user_id': 'u1', 'email': 'admin@example.com'})
    self.assertTrue(is_current_user_admin())

def test_returns_false_when_email_not_in_admin_emails(self):
    init_auth_decorators(None, {'auth': {'admin_emails': ['admin@example.com']}})
    UserContext.set_current_user({'user_id': 'u2', 'email': 'user@example.com'})
    self.assertFalse(is_current_user_admin())

def test_returns_false_when_not_initialized(self):
    # без изменений
    self.assertFalse(is_current_user_admin())
```

## Testing

Верификация вручную:
1. Добавить свой email в `auth.admin_emails` в `config.json`
2. Перезапустить приложение
3. Открыть `/jobs` — должны отображаться задачи всех пользователей
4. Убрать email из списка — поведение обычного пользователя возвращается

## Rollout

1. Развернуть код
2. В `config.json` заменить `admin_user_ids` на `admin_emails` со своим email
3. Перезапустить приложение

## Open Questions

Нет.
