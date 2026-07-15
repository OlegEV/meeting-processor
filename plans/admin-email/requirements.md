---
plan_slug: admin-email
phase: requirements
rig: meeting-processor
rig_root: /Users/egorovov/Documents/gc-spb/meeting-processor
artifact_root: /Users/egorovov/Documents/gc-spb/meeting-processor/plans
status: approved
created_at: 2026-06-15T00:00:00Z
updated_at: 2026-06-15T00:00:00Z
---

# Requirements: Идентификация администратора по email

## Problem Statement

Текущая реализация роли «администратор» хранит список `auth.admin_user_ids`
в `config.json` — это значения claim `sub` из JWT-токена. Claim `sub` является
непрозрачным идентификатором (например, UUID от провайдера идентификации).
Оператор системы не знает свой `sub` без декодирования токена вручную.

Email пользователя также передаётся в токене (claim `email`) и известен
оператору заранее — это привычный идентификатор.

## Solution

Заменить ключ `auth.admin_user_ids` на `auth.admin_emails` в `config.json`.
Функция `is_current_user_admin()` должна сравнивать email текущего
пользователя (из claim `email` через `UserContext.get_current_user_email()`)
со списком разрешённых emails.

Всё остальное поведение остаётся прежним: при пустом списке никто не является
администратором; изменение вступает в силу после перезапуска приложения.

## User Stories

### US-1: Оператор указывает администраторов по email

**Как** оператор системы,  
**я хочу** указывать администраторов через их email в `config.json`,  
**чтобы** не нужно было декодировать JWT-токен для получения `sub`.

Критерии приёмки:
- `config.json` содержит ключ `auth.admin_emails` (список строк, `[]` по умолчанию)
- Ключ `auth.admin_user_ids` удалён из `config.json`
- При пустом `admin_emails` никто не является администратором
- Изменение вступает в силу после перезапуска приложения

### US-2: Функция is_current_user_admin() использует email

**Как** система,  
**я хочу** проверять принадлежность к роли admin по email,  
**чтобы** логика авторизации соответствовала конфигурации.

Критерии приёмки:
- `is_current_user_admin()` читает `auth.admin_emails` из конфига
- Сравнение производится с `UserContext.get_current_user_email()`
- Если email текущего пользователя `None` — возвращает `False`
- Поведение всех остальных маршрутов (`/jobs`, `/status/<id>`) не меняется

## Out Of Scope

- Поддержка обоих форматов (`admin_user_ids` и `admin_emails`) одновременно
- Нормализация регистра email (сравнение case-sensitive как и раньше)
- Hot-reload конфига без перезапуска

## Other Notes

- `UserContext.get_current_user_email()` уже существует в `auth/user_context.py:54`
- Реэкспорт не нужен — `is_current_user_admin()` вызывает метод напрямую
- Логи и flash-сообщения остаются на русском языке
