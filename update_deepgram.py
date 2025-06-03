#!/usr/bin/env python3
"""
Скрипт для обновления Deepgram SDK до совместимой версии
"""

import subprocess
import sys

def run_command(cmd, description=""):
    """Выполняет команду"""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True)
        print("✅ Успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    """Обновляет Deepgram SDK"""
    print("🔧 Обновление Deepgram SDK")
    print("=" * 30)
    
    # Проверяем текущую версию
    try:
        import deepgram
        current_version = getattr(deepgram, '__version__', 'неизвестна')
        print(f"📊 Текущая версия: {current_version}")
    except ImportError:
        print("📊 Deepgram SDK не установлен")
    
    # Обновляем до последней версии
    commands = [
        ("pip install --upgrade deepgram-sdk", "Обновление Deepgram SDK"),
    ]
    
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            return False
    
    # Проверяем результат
    try:
        import deepgram
        new_version = getattr(deepgram, '__version__', 'неизвестна')
        print(f"🎉 Новая версия: {new_version}")
        
        # Тестируем импорт
        from deepgram import DeepgramClient, PrerecordedOptions
        print("✅ Импорт успешен")
        
        return True
    except ImportError as e:
        print(f"❌ Проблема с импортом: {e}")
        return False

if __name__ == "__main__":
    if main():
        print("\n🎉 Deepgram SDK обновлен успешно!")
        print("✨ Попробуйте снова: python meeting_processor.py")
    else:
        print("\n😞 Произошла ошибка при обновлении")