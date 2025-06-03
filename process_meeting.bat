@echo off
REM process_meeting.bat - Удобный скрипт для обработки встреч на Windows
setlocal enabledelayedexpansion

REM Проверяем аргументы
if "%~1"=="" goto :show_help
if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help
if "%~1"=="/?" goto :show_help

REM Проверяем зависимости
echo 🔍 Проверяю зависимости...

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден
    pause
    exit /b 1
)

ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  ffmpeg не найден. Запустите: python install_ffmpeg.py
)

if not exist "meeting_processor.py" (
    echo ❌ meeting_processor.py не найден в текущей директории
    pause
    exit /b 1
)

echo ✅ Зависимости проверены

REM Проверяем существование файла
set "input_file=%~1"
if not exist "!input_file!" (
    echo ❌ Файл не найден: !input_file!
    pause
    exit /b 1
)

REM Получаем размер файла
for %%A in ("!input_file!") do set "file_size=%%~zA"
set /a "size_mb=!file_size! / 1024 / 1024"
echo 📊 Размер файла: !size_mb! MB

REM Рекомендации по таймауту
if !size_mb! LSS 5 (
    echo 💡 Рекомендуемый таймаут: 180 сек
) else if !size_mb! LSS 15 (
    echo 💡 Рекомендуемый таймаут: 300 сек
) else if !size_mb! LSS 30 (
    echo 💡 Рекомендуемый таймаут: 600 сек
) else (
    echo 💡 Большой файл! Рекомендуется использовать process_long_audio.py
)

echo.
echo 🚀 Запускаю обработку файла: !input_file!
echo.

REM Запускаем Python скрипт с аргументами
python meeting_processor.py %*

if errorlevel 1 (
    echo.
    echo ❌ Произошла ошибка при обработке
    echo 💡 Попробуйте увеличить таймаут: %~nx0 "%~1" --timeout 600
    echo 💡 Или используйте специальный скрипт: python process_long_audio.py
    pause
    exit /b 1
) else (
    echo.
    echo 🎉 Обработка завершена успешно!
    echo 📁 Результаты сохранены в выходной директории
)

pause
exit /b 0

:show_help
echo.
echo 📋 Скрипт обработки видео/аудио встреч
echo.
echo Использование:
echo   %~nx0 [ФАЙЛ] [ОПЦИИ]
echo.
echo Примеры:
echo   %~nx0 meeting.mp4                    # Обработать видео с настройками по умолчанию
echo   %~nx0 audio.mp3 -o results          # Обработать аудио, результаты в папку results
echo   %~nx0 long_meeting.ogg -t 600       # Увеличить таймаут до 10 минут
echo   %~nx0 meeting.mp4 --keep-audio      # Сохранить извлеченный аудиофайл
echo.
echo Опции:
echo   -o, --output DIR        Директория для результатов
echo   -t, --timeout SEC       Таймаут Deepgram в секундах
echo   -c, --config FILE       Файл конфигурации
echo   -n, --names FILE        Файл конфигурации имен
echo   --chunks MIN            Размер частей в минутах
echo   --keep-audio            Сохранить аудиофайл
echo   -h, --help              Показать эту справку
echo.
echo Поддерживаемые форматы:
echo   Видео: MP4, AVI, MOV, MKV, WMV, WebM
echo   Аудио: MP3, OGG, WAV, FLAC, AAC, M4A
echo.
pause
exit /b 0