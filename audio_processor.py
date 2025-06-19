#!/usr/bin/env python3
"""
Модуль для обработки аудио и видео файлов
"""

import os
import subprocess
import json
from pathlib import Path
from typing import List, Optional, Tuple

class AudioProcessor:
    """Класс для обработки аудио и видео файлов"""
    
    def __init__(self):
        self.native_audio_formats = {'.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg'}
        self.convert_audio_formats = {'.wma', '.opus'}
        self.video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm'}
    
    def check_ffmpeg(self) -> bool:
        """Проверяет доступность ffmpeg"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def get_audio_info(self, file_path: str) -> Tuple[str, str, str]:
        """
        Получает информацию об аудио/видео файле
        
        Returns:
            (file_type, file_extension, duration_info)
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        # Проверяем, есть ли расширение
        if not extension:
            # Пытаемся определить расширение из имени файла
            filename = file_path.name.lower()
            print(f"⚠️ Файл без расширения: {file_path}")
            print(f"   Полное имя файла: '{filename}'")
            
            # Ищем известные расширения в конце имени файла
            all_extensions = self.native_audio_formats | self.convert_audio_formats | self.video_formats
            for ext in all_extensions:
                ext_without_dot = ext.lstrip('.')
                if filename.endswith(ext_without_dot):
                    extension = ext
                    print(f"   Найдено расширение в имени файла: '{extension}'")
                    break
            
            if not extension:
                return "unsupported", "", f"Не удалось определить расширение файла: {file_path.name}"
        
        # Определяем тип файла
        if extension in self.native_audio_formats:
            file_type = "native_audio"
        elif extension in self.convert_audio_formats:
            file_type = "convert_audio"
        elif extension in self.video_formats:
            file_type = "video"
        else:
            print(f"⚠️ Неподдерживаемое расширение: '{extension}' для файла: {file_path}")
            return "unsupported", extension, "Неподдерживаемый формат"
        
        # Получаем информацию о длительности
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                duration = float(info['format']['duration'])
                duration_str = f"{int(duration//60)}:{int(duration%60):02d}"
                
                if file_type == "native_audio":
                    return "native_audio", extension, f"Длительность: {duration_str} (нативная поддержка)"
                elif file_type == "convert_audio":
                    return "convert_audio", extension, f"Длительность: {duration_str} (требует конвертации)"
                else:
                    return "video", extension, f"Длительность: {duration_str}"
            else:
                return file_type, extension, "Информация о длительности недоступна"
        except Exception as e:
            print(f"⚠️ Не удалось получить информацию о файле: {e}")
            return file_type, extension, "Информация о длительности недоступна"
    
    def process_audio_file(self, audio_path: str, output_audio_path: str) -> bool:
        """Обрабатывает аудиофайл (конвертирует в нужный формат если необходимо)"""
        try:
            print(f"🎵 Обрабатываю аудиофайл {audio_path}...")
            
            if not self.check_ffmpeg():
                print("❌ ffmpeg не найден для обработки аудио!")
                return False
            
            cmd = [
                'ffmpeg', '-i', audio_path,           
                '-acodec', 'pcm_s16le',     
                '-ar', '44100',             
                '-ac', '2',                 
                '-y', output_audio_path           
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Аудио конвертировано в {output_audio_path}")
                return True
            else:
                print(f"❌ Ошибка конвертации: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при обработке аудио: {e}")
            return False

    def extract_audio_from_video(self, video_path: str, audio_path: str) -> bool:
        """Извлекает аудиодорожку из видеофайла"""
        try:
            print(f"🎬 Извлекаю аудио из видеофайла {video_path}...")
            
            if not self.check_ffmpeg():
                print("❌ ffmpeg не найден!")
                return False
            
            cmd = [
                'ffmpeg', '-i', video_path,        
                '-vn',                   
                '-acodec', 'pcm_s16le',  
                '-ar', '44100',          
                '-ac', '2',              
                '-y', audio_path               
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Аудио сохранено в {audio_path}")
                return True
            else:
                print(f"❌ Ошибка ffmpeg: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при извлечении аудио: {e}")
            return False

    def split_audio_file(self, audio_path: str, chunk_duration_minutes: int = 10) -> List[str]:
        """Разбивает длинный аудиофайл на части"""
        try:
            print(f"✂️ Разбиваю аудиофайл на части по {chunk_duration_minutes} минут...")
            
            audio_path_obj = Path(audio_path)
            audio_dir = audio_path_obj.parent
            audio_name = audio_path_obj.stem
            original_extension = audio_path_obj.suffix.lower()
            chunk_duration_seconds = chunk_duration_minutes * 60
            
            # Определяем, нужно ли конвертировать при разбивке
            keep_original_format = original_extension in self.native_audio_formats
            
            if keep_original_format:
                print(f"🎯 Сохраняю оригинальный формат {original_extension}")
                output_extension = original_extension
                audio_codec_params = ['-c:a', 'copy']
            else:
                print(f"🔄 Конвертирую в WAV для совместимости")
                output_extension = '.wav'
                audio_codec_params = ['-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2']
            
            # Получаем общую длительность
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print("❌ Не удалось получить информацию о длительности")
                return []
            
            info = json.loads(result.stdout)
            total_duration = float(info['format']['duration'])
            
            num_chunks = int(total_duration // chunk_duration_seconds) + 1
            print(f"📊 Создаю {num_chunks} частей в формате {output_extension}...")
            
            chunk_paths = []
            
            for i in range(num_chunks):
                start_time = i * chunk_duration_seconds
                chunk_path = audio_dir / f"{audio_name}_part_{i+1:02d}{output_extension}"
                
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-ss', str(start_time),
                    '-t', str(chunk_duration_seconds),
                    *audio_codec_params,
                    '-y', str(chunk_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    if chunk_path.stat().st_size > 1000:  # Проверяем, что файл не пустой
                        chunk_paths.append(str(chunk_path))
                        print(f"✅ Создана часть {i+1}: {chunk_path.name}")
                    else:
                        chunk_path.unlink()  # Удаляем пустой файл
                else:
                    print(f"❌ Ошибка создания части {i+1}")
            
            return chunk_paths
            
        except Exception as e:
            print(f"❌ Ошибка при разбивке аудио: {e}")
            return []
    
    def prepare_audio_file(self, input_file_path: str, file_type: str, output_dir: str, input_name: str) -> Tuple[Optional[str], bool]:
        """Подготавливает аудиофайл для транскрипции"""
        temp_audio_created = False
        
        if file_type == "native_audio":
            print("🚀 Используется нативная поддержка Deepgram - конвертация не требуется!")
            return input_file_path, temp_audio_created
            
        elif file_type == "convert_audio":
            audio_file_for_deepgram = f"{output_dir}/{input_name}.wav"
            if not self.process_audio_file(input_file_path, audio_file_for_deepgram):
                return None, False
            return audio_file_for_deepgram, True
            
        elif file_type == "video":
            audio_file_for_deepgram = f"{output_dir}/{input_name}.wav"
            if not self.extract_audio_from_video(input_file_path, audio_file_for_deepgram):
                return None, False
            return audio_file_for_deepgram, True
        
        else:
            print(f"❌ Неподдерживаемый тип файла: {file_type}")
            return None, False
