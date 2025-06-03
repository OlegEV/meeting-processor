@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ===============================================
echo 🛠️ Meeting Telegram Bot - Первоначальная настройка
echo ===============================================
echo.

REM Проверяем наличие Docker Desktop
echo 🔍 Проверяю Docker Desktop...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Desktop не найден!
    echo.
    echo 📥 Скачайте и установите Docker Desktop:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    echo После установки:
    echo 1. Перезагрузите компьютер
    echo 2. Запустите Docker Desktop
    echo 3. Дождитесь полной загрузки (обычно 1-2 минуты)
    echo 4. Запустите этот скрипт снова
    echo.
    pause
    exit /b 1
)

echo ✅ Docker Desktop найден

REM Проверяем, запущен ли Docker Desktop
echo 🔍 Проверяю статус Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Desktop не запущен!
    echo.
    echo ▶️ Запустите Docker Desktop и дождитесь полной загрузки
    echo ⏰ Обычно это занимает 1-2 минуты
    echo 💡 В системном трее должна появиться иконка Docker
    echo.
    echo После запуска Docker Desktop запустите этот скрипт снова
    pause
    exit /b 1
)

echo ✅ Docker Desktop запущен

REM Проверяем наличие необходимых Python файлов
echo.
echo 🔍 Проверяю наличие файлов системы...

set MISSING_FILES=0

if not exist "requirements.txt" (
    echo ❌ requirements.txt не найден
    set MISSING_FILES=1
)

if not exist "Dockerfile" (
    echo ❌ Dockerfile не найден
    set MISSING_FILES=1
)

if not exist "docker-compose.yml" (
    echo ❌ docker-compose.yml не найден
    set MISSING_FILES=1
)

if %MISSING_FILES%==1 (
    echo.
    echo ❌ Обнаружены отсутствующие файлы!
    echo.
    echo Убедитесь, что в папке присутствуют все необходимые файлы:
    echo - requirements.txt         (Python зависимости)
    echo - Dockerfile               (конфигурация Docker)
    echo - docker-compose.yml       (Docker Compose)
    echo - Все остальные *.py файлы (модули системы)
    echo.
    pause
    exit /b 1
)

echo ✅ Основные файлы системы найдены

REM Создаем структуру рабочих директорий
echo.
echo 📁 Создаю рабочие директории...

if not exist "logs" (
    mkdir logs
    echo ✅ Создана директория logs/
) else (
    echo ✅ Директория logs/ уже существует
)

if not exist "temp_files" (
    mkdir temp_files
    echo ✅ Создана директория temp_files/
) else (
    echo ✅ Директория temp_files/ уже существует
)

if not exist "output" (
    mkdir output
    echo ✅ Создана директория output/
) else (
    echo ✅ Директория output/ уже существует
)

REM Проверяем наличие конфигурационных файлов
echo.
echo 🔍 Проверяю конфигурационные файлы...

set MISSING_CONFIG=0


REM Создаем .env файл, если его нет
if not exist ".env" (
    echo.
    echo 📝 Создаю файл .env для переменных окружения...
    
    REM Проверяем наличие примера
    if exist ".env.example" (
        copy .env.example .env >nul 2>&1
        echo ✅ Скопирован .env из .env.example
    ) else (
        REM Создаем базовый .env файл
        (
            echo # Telegram Bot Configuration
            echo TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
            echo.
            echo # API Keys
            echo DEEPGRAM_API_KEY=your_deepgram_api_key_here
            echo CLAUDE_API_KEY=your_claude_api_key_here
            echo.
            echo # Optional Settings
            echo LOG_LEVEL=INFO
            echo MAX_FILE_SIZE_MB=100
            echo PROCESSING_TIMEOUT=1800
        ) > .env
        echo ✅ Создан базовый файл .env
    )
) else (
    echo ✅ Файл .env уже существует
)


echo.
echo 🏗️ Собираю Docker образ...
echo Это может занять несколько минут при первом запуске...

docker-compose build
if errorlevel 1 (
    echo.
    echo ❌ Ошибка при сборке Docker образа!
    echo.
    echo Возможные причины:
    echo - Проблемы с интернет-соединением
    echo - Недостаточно места на диске
    echo - Docker Desktop работает нестабильно
    echo.
    echo Попробуйте:
    echo 1. Перезапустить Docker Desktop
    echo 2. Очистить Docker cache: docker system prune
    echo 3. Запустить этот скрипт снова
    echo.
    pause
    exit /b 1
)

echo ✅ Docker образ успешно собран

echo.
echo 🧪 Проверяю готовность системы...

REM Проверяем образ
docker images | findstr meeting-telegram-bot >nul
if errorlevel 1 (
    echo ❌ Docker образ не найден
) else (
    echo ✅ Docker образ готов
)

echo.
echo 📁 Рабочие директории:
if exist "logs" (echo ✅ logs/) else (echo ❌ logs/)
if exist "temp_files" (echo ✅ temp_files/) else (echo ❌ temp_files/)
if exist "output" (echo ✅ output/) else (echo ❌ output/)

echo.
echo ===============================================
echo ✅ Первоначальная настройка завершена!
echo ===============================================
echo.
echo 💡 Полезные команды:
echo    run_bot.bat           - управление ботом
echo    docker-compose logs   - просмотр логов
echo    docker-compose down   - остановка бота
echo.

pause