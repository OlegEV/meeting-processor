# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Meeting Processor: takes an audio/video recording of a meeting, transcribes it with Deepgram, and generates a structured Markdown protocol via Claude (accessed through OpenRouter). The processing core (`meeting_processor.py`) is used by the Flask web application and is also available through the CLI. Most code comments and user-facing strings are in Russian — preserve that language when editing them.

## Entry points

- **Web app** — `python run_web.py` for development, `gunicorn --config gunicorn.conf.py wsgi:application` for production. `wsgi.py` instantiates `WorkingMeetingWebApp` from `run_web.py`.
- **CLI** — `python meeting_processor.py <input_file> [--template ...] [--transcribe-only | --protocol-only <transcript>]`. Reads `config.json` for defaults; CLI args override.

API keys come from environment variables only (`DEEPGRAM_API_KEY`, `CLAUDE_API_KEY`, plus `CONFLUENCE_API_TOKEN` when relevant). `ConfigLoader.load_api_keys` does not read any JSON file — the legacy `api_keys.json` path in `config.json` is unused.

## Common commands

```bash
# Install deps
pip install -r requirements.txt
python install_ffmpeg.py        # ffmpeg is required for video → audio extraction

# Full pipeline (transcribe + protocol)
python meeting_processor.py meeting.mp4 --template standup

# Partial pipelines
python meeting_processor.py meeting.mp3 --transcribe-only
python meeting_processor.py --protocol-only meeting_transcript.txt --template business

# Web (dev / prod)
python run_web.py
gunicorn --config gunicorn.conf.py wsgi:application

# Docker (web app)
docker-compose up -d            # web exposed on host port 8001 → container 8000

# Tests — use the wrapper, not pytest directly, when you want category routing
python run_tests.py quick                                  # unit only
python run_tests.py full                                   # all + coverage
python run_tests.py --categories unit integration --verbose
python -m pytest tests/test_database_models.py::TestUser -v   # single test
```

## Architecture

### Core pipeline (`MeetingProcessor.process_meeting` in `meeting_processor.py`)

1. `AudioProcessor` (`audio_processor.py`) — inspects the input, extracts audio from video via ffmpeg, and converts non-native formats (`.wma`, `.opus`) to WAV. Native Deepgram formats (mp3/wav/flac/aac/m4a/ogg) skip conversion.
2. `TranscriptionService` (`transcription_service.py`) — calls Deepgram SDK v7 (`client.listen.v1.media.transcribe_file`) with retry/backoff. Long files are split into chunks of `chunk_duration_minutes` and re-stitched. Returns diarized text with `Speaker 0/1/...` labels.
3. `ProtocolGenerator` (`protocol_generator.py`) — feeds the raw transcript + selected template to Claude (via `OpenRouterClient`) to produce the protocol. If the upload contained `participants` (`full_name`, `company`, `position`), the list is stored in `jobs.metadata` and included in the prompt for speaker identification.
4. Outputs two files in `output_dir`: `<name>_transcript.txt` and `<name>_summary.md`.

Progress reporting goes through `progress_callback(progress: int, message: str)` — the web app wires this up to push live updates to the user. When editing the pipeline, preserve the percent milestones (5/10/15/25/50/80/95/100) so the existing UI stays calibrated.

`MeetingProcessor` also supports two partial modes: `transcribe_only` (skips Claude) and `generate_protocol_from_transcript` (skips Deepgram). The CLI's `--transcribe-only` and `--protocol-only` flags pass `"dummy"` as the unused API key — don't tighten validation in a way that breaks this.

### Templates (`meeting_templates.py`, `templates_config.json`)

`MeetingTemplates` resolves a `template_type` (e.g. `standard`, `business`, `standup`, `interview`, `auto`, ...) to a prompt. With `auto`, `meeting_type_keywords` in `templates_config.json` are matched against the transcript to pick a type. `custom_templates` lets users define their own without touching code — preserve `{datetime_info}` and `{transcript}` placeholders.

### Web app (`run_web.py`, ~116 KB single file)

Flask app served via gunicorn in production. Notable structural points:
- **Auth** is JWT-based via the `auth/` package. `create_auth_system(config)` returns `(token_validator, user_manager, auth_middleware, auth_teardown)`. Tokens come from the `X-Identity-Token` header (configurable). Routes are guarded with `@require_auth`, except public `/view/<job_id>/<type>` and `/download/<job_id>/<type>` links for protocols and transcripts. In `config.json`, `auth.debug_mode: true` enables a hardcoded debug user — turn this off for production.
- **Per-user file storage** lives under `web_output/<user_id>/...` (`user_files.structure: "user_based"`).
- **Database** is SQLite at `meeting_processor.db` by default, or PostgreSQL when `database.type` is `postgresql` or `DATABASE_URL` holds a `postgresql://` URL (see `POSTGRESQL_README.md`). Both go through `DatabaseManager` from `database/`. Models (`User`, `Job`) and the per-dialect migration SQL are in `database/models.py` (`DatabaseSchema.get_migration_sql(version, dialect)`); the `.sql` files in `database/migrations/` are reference copies of the SQLite schema.
- **SQL is written in the SQLite dialect** with `?` placeholders, in `DatabaseManager` and in raw queries in `run_web.py` (via `db_manager._get_connection()`). For PostgreSQL, `database/pg_adapter.py` wraps psycopg to mimic the sqlite3 connection/cursor/row API and translates placeholders. Keep new SQL portable: no `PRAGMA`, `INSERT OR REPLACE`, `AUTOINCREMENT`, `cursor.lastrowid` (use `RETURNING id`) or `datetime('now', ...)` (use `db_manager.sql_days_ago()` / `sql_next_day()`); always use `with db_manager._get_connection() as conn:` — on PostgreSQL the `with` block also closes the connection. A schema change needs a new migration version in both dialects. `migrate_sqlite_to_postgres.py` copies data from a SQLite file into PostgreSQL.
- **Background jobs** use a `ThreadPoolExecutor`; the `MeetingProcessor` instance is created per-job and its `progress_callback` writes progress into the `Job` row for the frontend to poll.
- **Confluence integration** is optional and lazy-imported. `confluence_client.py` (REST publishing) and `confluence_encryption.py` (per-user token storage) only load if their deps and config are present — keep the `try/except ImportError` guard around imports.

### Configuration files

- `config.json` — main config (paths, auth, database, openrouter, settings, deepgram_options, supported_formats, available_models, confluence). Loaded by `ConfigLoader.load_config`. `settings.deepgram_proxy` (`enabled`/`url`/`verify_ssl`/`ca_bundle`) routes Deepgram traffic through a forward proxy; `DEEPGRAM_PROXY_URL` overrides it everywhere.
- `templates_config.json` — single source of truth for the template list: `template_descriptions` (id → human label, used by web UI / CLI / `template_manager.py`), `meeting_type_keywords` and `auto_detection_settings` (consumed by `MeetingTemplates._detect_meeting_type`), plus `custom_templates`.

Config keys are read with conservative `dict.get(..., default)` calls — when adding a new setting, keep that pattern so older `config.json` files still load.

## Tests

Tests live in `tests/` and are grouped into categories (`unit`, `integration`, `security`, `performance`, `e2e`) by `run_tests.py`. They need only `pytest` (`pytest-cov` for `run_tests.py full`) and make no network calls. Most existing tests cover Confluence integration, the database layer, and Flask routes — there is little coverage of the audio/transcription path.

`tests/test_postgres_support.py` runs its server-backed tests only when `TEST_DATABASE_URL` points to a PostgreSQL server (each test uses its own temporary schema); otherwise they are skipped. Run them after touching `database/` or any SQL.

When writing Flask tests: `AUTH_DEBUG_MODE` from a local `.env` overrides `auth.debug_mode` of the test config, so pin it with `patch.dict(os.environ, ...)` while the app is created. With debug mode on, set `auth.debug_user` to the user that owns the test jobs; with it off, patch `app.token_validator.validate_request`. In `tearDown`, drop the app reference and call `gc.collect()` before deleting the temp database (open sqlite3 connections lock the file on Windows).

## Things to watch for

- **Single-file giants**: `run_web.py` (~3000 lines) and `web_templates.py` (~86 KB of HTML in Python strings) are intentionally monolithic. Prefer surgical edits over refactors unless asked.
- **No external resources in pages**: Bootstrap, Font Awesome (with fonts), marked and Chart.js are vendored under `static/vendor/` (versions in `static/vendor/README.md`) because CDNs are blocked on the target network. Never add `<script>`/`<link>` tags pointing to a CDN — put the file in `static/vendor/` instead; `test_pages_do_not_load_external_resources` enforces this.
- **Russian strings everywhere**: log messages, prompts, user-facing UI text, and exception messages are mostly Russian. New strings in user-visible paths should match.
- **Optional imports are load-bearing**: `MeetingTemplates` and Confluence modules are wrapped in `try/except ImportError` and the code degrades gracefully when they're missing. Don't convert these to hard imports.
- **Two Claude model id formats coexist**: legacy Anthropic ids (e.g. `claude-sonnet-4-20250514`) and OpenRouter ids (e.g. `anthropic/claude-sonnet-4.5`). `OpenRouterClient.get_openrouter_model_name` translates between them — route new code through the OpenRouter form.
- **`meeting_processor.db` is committed** to the repo as the dev database. Don't reset/migrate it without checking with the user.
