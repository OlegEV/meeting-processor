#!/usr/bin/env python3
"""
Примеры использования скрипта meeting_processor.py для разных форматов файлов
"""

from meeting_processor import MeetingProcessor

# Инициализация процессора
processor = MeetingProcessor(
    deepgram_api_key="your_deepgram_key",
    claude_api_key="your_openrouter_api_key"
)

# Настройка замен имен
name_mapping = {
    "Speaker 0": "Анна Петрова",
    "Speaker 1": "Иван Сидоров",
    "Speaker 2": "Мария Козлова"
}

# Примеры обработки разных форматов

# 1. Видеофайл MP4
print("=== Обработка видео MP4 ===")
processor.process_meeting(
    input_file_path="meeting_video.mp4",
    output_dir="output_video",
    name_mapping=name_mapping
)

# 2. Аудиофайл MP3
print("\n=== Обработка аудио MP3 ===")
processor.process_meeting(
    input_file_path="meeting_audio.mp3",
    output_dir="output_mp3",
    name_mapping=name_mapping
)

# 3. Аудиофайл OGG
print("\n=== Обработка аудио OGG ===")
processor.process_meeting(
    input_file_path="meeting_audio.ogg",
    output_dir="output_ogg",
    name_mapping=name_mapping
)

# 4. Массовая обработка файлов
print("\n=== Массовая обработка ===")
files_to_process = [
    "meeting1.mp4",
    "meeting2.mp3", 
    "meeting3.ogg",
    "meeting4.wav"
]

for file_path in files_to_process:
    if os.path.exists(file_path):
        print(f"\nОбрабатываю {file_path}...")
        output_dir = f"output_{Path(file_path).stem}"
        processor.process_meeting(
            input_file_path=file_path,
            output_dir=output_dir,
            name_mapping=name_mapping
        )
    else:
        print(f"Файл {file_path} не найден, пропускаю...")

print("\n🎉 Обработка завершена!")
