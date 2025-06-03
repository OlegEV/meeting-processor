#!/usr/bin/env python3
"""
Скрипт для тестирования функции разделения по спикерам (diarization) в Deepgram
"""

import os
import sys
from pathlib import Path
from meeting_processor import MeetingProcessor, load_config

def test_diarization_options():
    """Тестирует различные опции для разделения по спикерам"""
    
    print("🎤 ТЕСТ РАЗДЕЛЕНИЯ ПО СПИКЕРАМ (DIARIZATION)")
    print("=" * 60)
    
    # Получаем настройки
    config = load_config("config.json")
    
    DEEPGRAM_API_KEY = config.get("api_keys", {}).get("deepgram")
    CLAUDE_API_KEY = config.get("api_keys", {}).get("claude", "test")
    
    if not DEEPGRAM_API_KEY or DEEPGRAM_API_KEY == "your_deepgram_api_key_here":
        print("❌ API ключ Deepgram не настроен в config.json")
        return
    
    # Спрашиваем файл для тестирования
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        test_file = input("📁 Введите путь к аудиофайлу для тестирования: ").strip().strip('"')
    
    if not os.path.exists(test_file):
        print(f"❌ Файл не найден: {test_file}")
        return
    
    print(f"📄 Тестирую файл: {test_file}")
    
    # Тестируем разные настройки diarization
    test_configs = [
        {
            "name": "Базовая диаризация",
            "options": {"diarize": True, "punctuate": True, "smart_format": True},
            "description": "Стандартные настройки с разделением по спикерам"
        },
        {
            "name": "Диаризация + utterances",
            "options": {"diarize": True, "utterances": True, "punctuate": True},
            "description": "С дополнительными метаданными высказываний"
        },
        {
            "name": "Только базовый текст",
            "options": {"diarize": False, "punctuate": True},
            "description": "Без разделения по спикерам для сравнения"
        }
    ]
    
    results = []
    
    for i, test_config in enumerate(test_configs, 1):
        print(f"\n{'='*50}")
        print(f"🧪 ТЕСТ {i}: {test_config['name']}")
        print(f"📝 {test_config['description']}")
        print(f"⚙️ Опции: {test_config['options']}")
        print(f"{'='*50}")
        
        # Создаем процессор с тестовыми настройками
        processor = MeetingProcessor(
            DEEPGRAM_API_KEY, 
            CLAUDE_API_KEY, 
            deepgram_timeout=300,
            deepgram_options=test_config['options']
        )
        
        # Берем небольшую часть файла для тестирования
        test_audio_path = create_test_sample(test_file, duration_seconds=60)
        
        if test_audio_path:
            try:
                # Транскрибируем
                with open(test_audio_path, "rb") as f:
                    audio_data = f.read()
                
                transcript = processor.transcribe_audio_with_timeout(audio_data, timeout_override=120)
                
                if transcript:
                    # Анализируем результат
                    speaker_count = transcript.count("Speaker")
                    lines_count = len([line for line in transcript.split('\n') if line.strip()])
                    
                    result = {
                        "config": test_config['name'],
                        "speaker_count": speaker_count,
                        "lines_count": lines_count,
                        "has_speakers": "Speaker" in transcript,
                        "transcript_preview": transcript[:300] + "..." if len(transcript) > 300 else transcript
                    }
                    
                    results.append(result)
                    
                    print(f"✅ Результат:")
                    print(f"   🎭 Упоминаний спикеров: {speaker_count}")
                    print(f"   📄 Строк текста: {lines_count}")
                    print(f"   🎯 Есть разделение: {'Да' if result['has_speakers'] else 'Нет'}")
                    print(f"   📝 Превью:")
                    print(f"   {result['transcript_preview']}")
                    
                else:
                    print(f"❌ Транскрипция не удалась")
                    results.append({"config": test_config['name'], "error": "Транскрипция не удалась"})
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                results.append({"config": test_config['name'], "error": str(e)})
            
            finally:
                # Удаляем тестовый файл
                try:
                    os.remove(test_audio_path)
                except:
                    pass
        else:
            print(f"❌ Не удалось создать тестовый образец")
    
    # Показываем сводку результатов
    print(f"\n{'='*60}")
    print(f"📊 СВОДКА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
    print(f"{'='*60}")
    
    for result in results:
        if "error" not in result:
            print(f"🧪 {result['config']}:")
            print(f"   🎭 Спикеров: {result['speaker_count']}")
            print(f"   🎯 Разделение: {'✅ Есть' if result['has_speakers'] else '❌ Нет'}")
            print(f"   📄 Строк: {result['lines_count']}")
        else:
            print(f"🧪 {result['config']}: ❌ {result['error']}")
        print()
    
    # Рекомендации
    best_result = max([r for r in results if "error" not in r], 
                     key=lambda x: x['speaker_count'], default=None)
    
    if best_result:
        print(f"💡 РЕКОМЕНДАЦИЯ:")
        print(f"Лучший результат показал: {best_result['config']}")
        print(f"Найдено {best_result['speaker_count']} упоминаний спикеров")
    
    print(f"\n🔧 ДЛЯ УЛУЧШЕНИЯ ДИАРИЗАЦИИ:")
    print(f"1. Убедитесь, что в записи несколько говорящих")
    print(f"2. Качество аудио должно быть достаточным")
    print(f"3. Говорящие должны различаться по голосу")
    print(f"4. Попробуйте модель 'nova-2' для лучших результатов")

def create_test_sample(input_file: str, duration_seconds: int = 60) -> str:
    """Создает тестовый образец файла"""
    try:
        output_file = f"test_sample_{duration_seconds}s.wav"
        
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-t', str(duration_seconds),
            '-acodec', 'pcm_s16le',
            '-ar', '44100',
            '-ac', '2',
            '-y',
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"📄 Создан тестовый образец: {output_file}")
            return output_file
        else:
            print(f"❌ Ошибка создания образца: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def show_diarization_tips():
    """Показывает советы по улучшению диаризации"""
    
    print(f"\n💡 СОВЕТЫ ПО УЛУЧШЕНИЮ РАЗДЕЛЕНИЯ ПО СПИКЕРАМ:")
    print("=" * 55)
    
    tips = [
        "🎤 Качество записи - чем лучше качество, тем лучше диаризация",
        "👥 Количество спикеров - оптимально 2-6 участников",
        "🔊 Различия в голосах - мужские/женские голоса разделяются лучше",
        "⏱️ Длительность высказываний - короткие реплики хуже распознаются",
        "🔇 Фоновый шум - минимизируйте посторонние звуки",
        "📍 Расположение микрофонов - равномерное покрытие всех участников",
        "🗣️ Четкая речь - избегайте одновременных разговоров",
        "⚙️ Модель nova-2 - лучшая модель для диаризации"
    ]
    
    for tip in tips:
        print(f"  {tip}")
    
    print(f"\n🔧 НАСТРОЙКИ В CONFIG.JSON ДЛЯ ЛУЧШЕЙ ДИАРИЗАЦИИ:")
    print("""
{
  "deepgram_options": {
    "diarize": true,
    "punctuate": true,
    "smart_format": true,
    "paragraphs": true,
    "utterances": false
  }
}
""")

def main():
    """Основная функция"""
    if len(sys.argv) > 1:
        test_diarization_options()
    else:
        print("🎤 ТЕСТИРОВАНИЕ ДИАРИЗАЦИИ DEEPGRAM")
        print("=" * 40)
        print("Этот скрипт поможет протестировать разделение по спикерам")
        print("и найти оптимальные настройки для вашего аудио.")
        print()
        
        choice = input("Выберите действие:\n1. Тест диаризации\n2. Показать советы\n3. Выход\nВвод: ")
        
        if choice == "1":
            test_diarization_options()
        elif choice == "2":
            show_diarization_tips()
        else:
            print("👋 До свидания!")

if __name__ == "__main__":
    import subprocess
    main()