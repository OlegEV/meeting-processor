@echo off
chcp 65001
setlocal enabledelayedexpansion
echo ===============================================
echo 🤖 Meeting Telegram Bot - Docker Launcher
echo ===============================================
echo.

REM Проверяем наличие Docker Desktop
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Desktop не найден!
    echo Установите Docker Desktop и убедитесь, что он запущен.
    pause
    exit /b 1
)

echo ✅ Docker Desktop найден

REM Проверяем, запущен ли Docker Desktop
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Desktop не запущен!
    echo Запустите Docker Desktop и повторите попытку.
    pause
    exit /b 1
)

echo ✅ Docker Desktop запущен

REM Создаем необходимые директории
if not exist "logs" mkdir logs
if not exist "temp_files" mkdir temp_files
if not exist "output" mkdir output

echo ✅ Рабочие директории проверены

REM Проверяем наличие файла .env
if not exist ".env" (
    echo.
    echo ⚠️ Файл .env не найден!
    echo Создаю пример файла .env...
    echo.
    
    (
        echo # Telegram Bot Configuration
        echo TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
        echo.
        echo # API Keys
        echo DEEPGRAM_API_KEY=your_deepgram_api_key_here
        echo CLAUDE_API_KEY=your_claude_api_key_here
    ) > .env
    
    echo ✅ Создан файл .env
    echo.
    echo ⚠️ ВАЖНО: Отредактируйте файл .env и добавьте ваши API ключи!
    echo.
    pause
)

REM Проверяем наличие основных конфигурационных файлов
if not exist "bot_config.json" (
    echo ⚠️ Файл bot_config.json не найден!
    echo Создаю базовую конфигурацию...
    
    (
        echo {
        echo   "telegram": {
        echo     "bot_token": "",
        echo     "allowed_users": [],
        echo     "admin_users": [],
        echo     "max_file_size_mb": 100
        echo   },
        echo   "processing": {
        echo     "default_template": "standard",
        echo     "max_concurrent_jobs": 3,
        echo     "processing_timeout": 1800
        echo   },
        echo   "notifications": {
        echo     "send_progress_updates": true,
        echo     "notify_on_completion": true,
        echo     "notify_on_error": true
        echo   }
        echo }
    ) > bot_config.json
    
    echo ✅ Создан bot_config.json
)

if not exist "api_keys.json" (
    echo ⚠️ Файл api_keys.json не найден!
    echo Создаю конфигурацию API ключей...
    
    (
        echo {
        echo   "api_keys": {
        echo     "deepgram": "",
        echo     "claude": ""
        echo   }
        echo }
    ) > api_keys.json
    
    echo ✅ Создан api_keys.json
)

if not exist "config.json" (
    echo ⚠️ Файл config.json не найден!
    echo Создаю основную конфигурацию...
    
    (
        echo {
        echo   "settings": {
        echo     "language": "ru",
        echo     "deepgram_model": "nova-2",
        echo     "claude_model": "claude-sonnet-4-20250514",
        echo     "template_type": "standard"
        echo   }
        echo }
    ) > config.json
    
    echo ✅ Создан config.json
)

if not exist "templates_config.json" (
    echo ⚠️ Файл templates_config.json не найден!
    echo Создаю конфигурацию шаблонов...
    
    (
        echo {
        echo   "default_template": "standard",
        echo   "template_settings": {
        echo     "include_technical_info": true,
        echo     "include_file_datetime": true,
        echo     "language": "ru",
        echo     "max_tokens": 2000
        echo   }
        echo }
    ) > templates_config.json
    
    echo ✅ Создан templates_config.json
)

if not exist "names_config.json" (
    echo ⚠️ Файл names_config.json не найден!
    echo Создаю конфигурацию имен...
    
    (
        echo {
        echo   "name_mapping": {},
        echo   "auto_replace": false
        echo }
    ) > names_config.json
    
    echo ✅ Создан names_config.json
)

if not exist "team_config.json" (
    echo ⚠️ Файл team_config.json не найден!
    echo Создаю конфигурацию команды...
    
    (
        echo {
        echo   "teams": {},
        echo   "enable_team_identification": false
        echo }
    ) > team_config.json
    
    echo ✅ Создан team_config.json
)

:main_menu
echo.
echo 📋 Выберите действие:
echo 1. Запустить бота (docker-compose up)
echo 2. Запустить в фоне (docker-compose up -d)
echo 3. Пересобрать и запустить (docker-compose up --build)
echo 4. Остановить бота
echo 5. Показать логи
echo 6. Статус контейнера
echo 7. Очистить контейнеры и образы
echo 8. Проверить конфигурацию
echo 0. Выход
echo.

set /p choice="Введите номер (0-8): "

if "%choice%"=="1" goto :run_foreground
if "%choice%"=="2" goto :run_background
if "%choice%"=="3" goto :rebuild_run
if "%choice%"=="4" goto :stop_bot
if "%choice%"=="5" goto :show_logs
if "%choice%"=="6" goto :show_status
if "%choice%"=="7" goto :cleanup
if "%choice%"=="8" goto :check_config
if "%choice%"=="0" goto :exit

echo ❌ Неверный выбор!
pause
goto :main_menu

:run_foreground
echo.
echo 🚀 Запускаю бота...
docker-compose up
goto :end

:run_background
echo.
echo 🚀 Запускаю бота в фоне...
docker-compose up -d
if errorlevel 0 (
    echo ✅ Бот запущен в фоне
    echo 📋 Используйте команду 5 для просмотра логов
)
pause
goto :main_menu

:rebuild_run
echo.
echo 🔨 Пересобираю и запускаю бота...
docker-compose up --build
goto :end

:stop_bot
echo.
echo 🛑 Останавливаю бота...
docker-compose down
if errorlevel 0 (
    echo ✅ Бот остановлен
)
pause
goto :main_menu

:show_logs
echo.
echo 📋 Показываю логи (Ctrl+C для выхода)...
docker-compose logs -f telegram-bot
goto :main_menu

:show_status
echo.
echo 📊 Статус контейнера:
docker-compose ps
echo.
echo 📈 Использование ресурсов:
docker stats meeting-telegram-bot --no-stream
pause
goto :main_menu

:check_config
echo.
echo 🔍 Проверка конфигурации:
echo.
echo 📁 Файлы конфигурации:
if exist "bot_config.json" (echo ✅ bot_config.json) else (echo ❌ bot_config.json)
if exist "api_keys.json" (echo ✅ api_keys.json) else (echo ❌ api_keys.json)
if exist "config.json" (echo ✅ config.json) else (echo ❌ config.json)
if exist "templates_config.json" (echo ✅ templates_config.json) else (echo ❌ templates_config.json)
if exist "names_config.json" (echo ✅ names_config.json) else (echo ❌ names_config.json)
if exist "team_config.json" (echo ✅ team_config.json) else (echo ❌ team_config.json)
echo.
echo 📁 Рабочие директории:
if exist "logs" (echo ✅ logs/) else (echo ❌ logs/)
if exist "temp_files" (echo ✅ temp_files/) else (echo ❌ temp_files/)
if exist "output" (echo ✅ output/) else (echo ❌ output/)
echo.
echo 🔑 Переменные окружения (.env):
if exist ".env" (echo ✅ .env найден) else (echo ❌ .env не найден)
pause
goto :main_menu

:cleanup
echo.
echo ⚠️ Это удалит все контейнеры и образы бота!
set /p confirm="Продолжить? (y/N): "
if /i "%confirm%"=="y" (
    echo 🗑️ Очищаю контейнеры и образы...
    docker-compose down --rmi all --volumes
    docker system prune -f
    echo ✅ Очистка завершена
) else (
    echo ❌ Очистка отменена
)
pause
goto :main_menu

:exit
echo.
echo 👋 До свидания!
exit /b 0

:end
echo.
echo 🏁 Бот завершил работу
pause