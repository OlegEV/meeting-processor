# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Meeting Processor: takes an audio/video recording of a meeting, transcribes it with Deepgram, identifies participants from a team config, and generates a structured Markdown protocol via Claude (accessed through OpenRouter). The same processing core (`meeting_processor.py`) is exposed through three frontends: a CLI, a Flask web app, and a Telegram bot. Most code comments and user-facing strings are in Russian — preserve that language when editing them.

## Entry points

There are three independent runtime entry points sharing the same processing core:

- **CLI** — `python meeting_processor.py <input_file> [--template ...] [--transcribe-only | --protocol-only <transcript>]`. Reads `config.json` for defaults; CLI args override.
- **Web app** — `python run_web.py` for development, `gunicorn --config gunicorn.conf.py wsgi:application` for production. `wsgi.py` instantiates `WorkingMeetingWebApp` from `run_web.py`.
- **Telegram bot** — `python telegram_bot.py`. Uses `bot_config.json` for allowed/admin user IDs and limits. Independent from the web app.

API keys come from environment variables only (`DEEPGRAM_API_KEY`, `CLAUDE_API_KEY`, plus `TELEGRAM_BOT_TOKEN`, `CONFLUENCE_API_TOKEN` when relevant). `ConfigLoader.load_api_keys` does not read any JSON file — the legacy `api_keys.json` path in `config.json` is unused.

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

# Docker (web + bot together)
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
2. `TranscriptionService` (`transcription_service.py`) — calls Deepgram SDK v5 with retry/backoff. Long files are split into chunks of `chunk_duration_minutes` and re-stitched. Returns diarized text with `Speaker 0/1/...` labels.
3. `ProtocolGenerator` (`protocol_generator.py`) — first pass: feeds the raw transcript + selected template to Claude (via `OpenRouterClient`) to produce a draft protocol.
4. `TeamIdentifier` + `SpeakerMapper` (`team_identifier.py`, `speaker_mapper.py`) — analyse both protocol and transcript against `team_config.json` to map `Speaker N` → real names. Produces a combined replacement map.
5. Replacements are applied to the transcript; if any participants were identified, the protocol is **regenerated** with team context for higher quality.
6. Outputs three files in `output_dir`: `<name>_transcript.txt`, `<name>_summary.md`, `<name>_team_info.txt`.

Progress reporting goes through `progress_callback(progress: int, message: str)` — the web app and bot both wire this up to push live updates to the user. When editing the pipeline, preserve the percent milestones (5/10/15/25/50/65/80/90/95/100) so existing UIs stay calibrated.

`MeetingProcessor` also supports two partial modes: `transcribe_only` (skips Claude) and `generate_protocol_from_transcript` (skips Deepgram). The CLI's `--transcribe-only` and `--protocol-only` flags pass `"dummy"` as the unused API key — don't tighten validation in a way that breaks this.

### Templates (`meeting_templates.py`, `templates_config.json`)

`MeetingTemplates` resolves a `template_type` (e.g. `standard`, `business`, `standup`, `interview`, `auto`, ...) to a prompt. With `auto`, `meeting_type_keywords` in `templates_config.json` are matched against the transcript to pick a type. `custom_templates` lets users define their own without touching code — preserve `{datetime_info}` and `{transcript}` placeholders.

### Web app (`run_web.py`, ~116 KB single file)

Flask app served via gunicorn in production. Notable structural points:
- **Auth** is JWT-based via the `auth/` package. `create_auth_system(config)` returns `(token_validator, user_manager, auth_middleware, auth_teardown)`. Tokens come from the `X-Identity-Token` header (configurable). Routes are guarded with `@require_auth`. In `config.json`, `auth.debug_mode: true` enables a hardcoded debug user — turn this off for production.
- **Per-user file storage** lives under `web_output/<user_id>/...` (`user_files.structure: "user_based"`).
- **Database** is SQLite at `meeting_processor.db`, accessed via `DatabaseManager` from `database/`. Models (`User`, `Job`) are in `database/models.py`; migrations live in `database/migrations/`.
- **Background jobs** use a `ThreadPoolExecutor`; the `MeetingProcessor` instance is created per-job and its `progress_callback` writes progress into the `Job` row for the frontend to poll.
- **Confluence integration** is optional and lazy-imported. `confluence_client.py` (REST publishing) and `confluence_encryption.py` (per-user token storage) only load if their deps and config are present — keep the `try/except ImportError` guard around imports.

### Telegram bot (`telegram_bot.py`)

Uses `python-telegram-bot` v20 (async). Accepts file uploads and HTTP URLs (handled by `url_file_processor.py`). Maintains a per-chat conversation state for picking the template. Long-running processing runs in a worker; progress updates edit a status message in the chat.

### Configuration files

- `config.json` — main config (paths, auth, database, openrouter, settings, deepgram_options, supported_formats, claude_models, available_models, confluence). Loaded by `ConfigLoader.load_config`.
- `team_config.json` — known team members for speaker identification.
- `templates_config.json` — single source of truth for the template list: `template_descriptions` (id → human label, used by web UI / CLI / `template_manager.py`), `meeting_type_keywords` and `auto_detection_settings` (consumed by `MeetingTemplates._detect_meeting_type`), plus `custom_templates`.
- `bot_config.json` — Telegram bot allow-list, admin IDs, file size limits.
- `names_config.json` — legacy manual `Speaker N → name` map; only used as a fallback when `TeamIdentifier` is not available.

Config keys are read with conservative `dict.get(..., default)` calls — when adding a new setting, keep that pattern so older `config.json` files still load.

## Tests

Tests live in `tests/` and are grouped into categories (`unit`, `integration`, `security`, `frontend`, `performance`, `e2e`) by `run_tests.py`. The frontend tests use Selenium and need Chrome + `webdriver-manager`; performance tests need `psutil`; both are optional. Most existing tests cover Confluence integration, the database layer, and Flask routes — there is little coverage of the audio/transcription path.

## Things to watch for

- **Single-file giants**: `run_web.py` (~3000 lines), `web_templates.py` (~86 KB of HTML in Python strings), and `telegram_bot.py` (~110 KB) are intentionally monolithic. Prefer surgical edits over refactors unless asked.
- **Russian strings everywhere**: log messages, prompts, user-facing UI text, and exception messages are mostly Russian. New strings in user-visible paths should match.
- **Optional imports are load-bearing**: `MeetingTemplates`, `TeamIdentifier`, `SpeakerMapper`, and Confluence modules are wrapped in `try/except ImportError` and the code degrades gracefully when they're missing. Don't convert these to hard imports.
- **Two Claude model id formats coexist**: legacy Anthropic ids (e.g. `claude-sonnet-4-20250514`) and OpenRouter ids (e.g. `anthropic/claude-sonnet-4.5`). `OpenRouterClient.get_openrouter_model_name` translates between them — route new code through the OpenRouter form.
- **`meeting_processor.db` is committed** to the repo as the dev database. Don't reset/migrate it without checking with the user.
