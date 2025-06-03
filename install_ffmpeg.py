#!/usr/bin/env python3
"""
Скрипт для установки и проверки ffmpeg
"""

import subprocess
import sys
import os
import platform
import urllib.request
import zipfile
from pathlib import Path

def run_command(cmd, shell=True):
    """Выполняет команду и возвращает результат"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_ffmpeg():
    """Проверяет наличие ffmpeg"""
    success, stdout, stderr = run_command(['ffmpeg', '-version'], shell=False)
    if success:
        version_line = stdout.split('\n')[0]
        print(f"✅ ffmpeg найден: {version_line}")
        return True
    else:
        print("❌ ffmpeg не найден")
        return False

def install_ffmpeg_windows():
    """Устанавливает ffmpeg на Windows"""
    print("🔽 Загружаю ffmpeg для Windows...")
    
    # URL для скачивания ffmpeg (статическая сборка)
    ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    try:
        # Создаем папку для ffmpeg
        ffmpeg_dir = Path.home() / "ffmpeg"
        ffmpeg_dir.mkdir(exist_ok=True)
        
        zip_path = ffmpeg_dir / "ffmpeg.zip"
        
        # Скачиваем ffmpeg
        print("📥 Скачиваю ffmpeg...")
        urllib.request.urlretrieve(ffmpeg_url, zip_path)
        
        # Распаковываем
        print("📦 Распаковываю ffmpeg...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        
        # Находим исполняемый файл
        for item in ffmpeg_dir.rglob("ffmpeg.exe"):
            ffmpeg_exe = item
            break
        else:
            print("❌ ffmpeg.exe не найден в архиве")
            return False
        
        # Добавляем в PATH
        ffmpeg_bin_dir = ffmpeg_exe.parent
        print(f"📍 ffmpeg расположен в: {ffmpeg_bin_dir}")
        
        # Проверяем, есть ли уже в PATH
        current_path = os.environ.get('PATH', '')
        if str(ffmpeg_bin_dir) not in current_path:
            print("⚙️ Добавляю ffmpeg в PATH...")
            
            # Временно добавляем в PATH для текущей сессии
            os.environ['PATH'] = f"{ffmpeg_bin_dir};{current_path}"
            
            # Информируем пользователя о постоянном добавлении
            print(f"💡 Для постоянного использования добавьте в PATH:")
            print(f"   {ffmpeg_bin_dir}")
            print("   Или выполните команду:")
            print(f'   setx PATH "%PATH%;{ffmpeg_bin_dir}"')
        
        # Удаляем архив
        zip_path.unlink()
        
        # Проверяем установку
        if check_ffmpeg():
            print("✅ ffmpeg успешно установлен!")
            return True
        else:
            print("❌ Не удалось настроить ffmpeg")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при установке ffmpeg: {e}")
        return False

def install_ffmpeg_macos():
    """Устанавливает ffmpeg на macOS"""
    print("🍺 Попытка установки через Homebrew...")
    
    # Проверяем наличие Homebrew
    brew_available, _, _ = run_command(['brew', '--version'], shell=False)
    
    if brew_available:
        success, stdout, stderr = run_command(['brew', 'install', 'ffmpeg'], shell=False)
        if success:
            print("✅ ffmpeg установлен через Homebrew!")
            return True
        else:
            print(f"❌ Ошибка установки через Homebrew: {stderr}")
    else:
        print("❌ Homebrew не найден")
        print("💡 Установите Homebrew: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        print("   Затем выполните: brew install ffmpeg")
    
    return False

def install_ffmpeg_linux():
    """Устанавливает ffmpeg на Linux"""
    print("🐧 Попытка установки через пакетный менеджер...")
    
    # Пробуем разные пакетные менеджеры
    managers = [
        (['apt', 'update'], ['apt', 'install', '-y', 'ffmpeg']),
        (['yum', 'install', '-y', 'ffmpeg'], None),
        (['dnf', 'install', '-y', 'ffmpeg'], None),
        (['pacman', '-S', '--noconfirm', 'ffmpeg'], None),
    ]
    
    for update_cmd, install_cmd in managers:
        if update_cmd:
            print(f"🔄 Обновляю пакеты...")
            run_command(update_cmd, shell=False)
        
        print(f"📦 Устанавливаю ffmpeg...")
        success, stdout, stderr = run_command(install_cmd, shell=False)
        
        if success:
            print("✅ ffmpeg установлен!")
            return True
    
    print("❌ Не удалось установить ffmpeg автоматически")
    print("💡 Попробуйте вручную:")
    print("   Ubuntu/Debian: sudo apt install ffmpeg")
    print("   CentOS/RHEL: sudo yum install ffmpeg")
    print("   Fedora: sudo dnf install ffmpeg")
    print("   Arch: sudo pacman -S ffmpeg")
    
    return False

def main():
    """Основная функция"""
    print("🎬 УСТАНОВКА FFMPEG")
    print("=" * 40)
    
    # Проверяем текущее состояние
    if check_ffmpeg():
        print("🎉 ffmpeg уже установлен и готов к использованию!")
        return True
    
    # Определяем операционную систему
    system = platform.system().lower()
    print(f"🖥️ Операционная система: {system}")
    
    # Устанавливаем в зависимости от ОС
    if system == "windows":
        success = install_ffmpeg_windows()
    elif system == "darwin":
        success = install_ffmpeg_macos()
    elif system == "linux":
        success = install_ffmpeg_linux()
    else:
        print(f"❌ Неподдерживаемая ОС: {system}")
        return False
    
    if success:
        print("\n🎉 ffmpeg готов к использованию!")
        print("✨ Теперь вы можете запустить: python meeting_processor.py")
        return True
    else:
        print("\n😞 Не удалось установить ffmpeg автоматически")
        print("💡 Скачайте ffmpeg вручную с https://ffmpeg.org/download.html")
        return False

if __name__ == "__main__":
    main()