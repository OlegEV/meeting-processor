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
        
        # Совместимость кодеков с контейнерами
        self.codec_container_compatibility = {
            '.ogg': {'vorbis', 'opus', 'flac'},
            '.mp3': {'mp3'},
            '.wav': {'pcm_s16le', 'pcm_s24le', 'pcm_s32le', 'pcm_f32le', 'pcm_f64le'},
            '.flac': {'flac'},
            '.aac': {'aac'},
            '.m4a': {'aac', 'alac'}
        }
    
    def check_ffmpeg(self) -> bool:
        """Проверяет доступность ffmpeg"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _is_codec_compatible_with_container(self, codec_name: str, container_extension: str) -> bool:
        """Проверяет совместимость кодека с контейнером"""
        if container_extension not in self.codec_container_compatibility:
            return False
        
        compatible_codecs = self.codec_container_compatibility[container_extension]
        return codec_name.lower() in compatible_codecs
    
    def _get_best_container_for_codec(self, codec_name: str) -> Tuple[str, List[str]]:
        """Возвращает лучший контейнер для данного кодека"""
        if not codec_name:
            return '.wav', ['-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2']
        
        codec_lower = codec_name.lower()
        
        # Ищем подходящий контейнер для кодека
        for container, compatible_codecs in self.codec_container_compatibility.items():
            if codec_lower in compatible_codecs:
                return container, ['-c:a', 'copy']
        
        # Если не нашли подходящий контейнер, используем WAV
        return '.wav', ['-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2']
    
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
            
            # Проверяем доступность ffmpeg
            if not self.check_ffmpeg():
                print("❌ ffmpeg не найден! Установите ffmpeg для разбиения файлов.")
                return []
            
            audio_path_obj = Path(audio_path)
            
            # Проверяем существование файла
            if not audio_path_obj.exists():
                print(f"❌ Файл не найден: {audio_path}")
                return []
            
            # Проверяем размер файла
            file_size = audio_path_obj.stat().st_size
            if file_size == 0:
                print(f"❌ Файл пустой: {audio_path}")
                return []
            
            print(f"📁 Исходный файл: {audio_path_obj.name} ({file_size / (1024*1024):.1f} MB)")
            
            audio_dir = audio_path_obj.parent
            audio_name = audio_path_obj.stem
            original_extension = audio_path_obj.suffix.lower()
            chunk_duration_seconds = chunk_duration_minutes * 60
            
            # Получаем информацию о кодеке файла
            cmd_probe = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', str(audio_path)]
            result_probe = subprocess.run(cmd_probe, capture_output=True, text=True)
            
            codec_name = None
            if result_probe.returncode == 0:
                try:
                    streams_info = json.loads(result_probe.stdout)
                    if 'streams' in streams_info and len(streams_info['streams']) > 0:
                        codec_name = streams_info['streams'][0].get('codec_name', '')
                        print(f"🔍 Обнаружен кодек: {codec_name}")
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Определяем, можно ли сохранить оригинальный формат
            can_keep_original = (
                original_extension in self.native_audio_formats and
                codec_name and
                self._is_codec_compatible_with_container(codec_name, original_extension)
            )
            
            if can_keep_original:
                print(f"🎯 Сохраняю оригинальный формат {original_extension}")
                output_extension = original_extension
                audio_codec_params = ['-c:a', 'copy']
            else:
                # Выбираем подходящий контейнер для кодека
                output_extension, audio_codec_params = self._get_best_container_for_codec(codec_name)
                if original_extension in self.native_audio_formats:
                    print(f"🔄 Кодек {codec_name} несовместим с контейнером {original_extension}")
                    print(f"   Сохраняю в формате {output_extension} с копированием кодека")
                else:
                    print(f"🔄 Сохраняю в подходящем формате {output_extension}")
            
            # Получаем общую длительность
            print("🔍 Анализирую длительность файла...")
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(audio_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print("❌ Не удалось получить информацию о длительности")
                print(f"   Команда: {' '.join(cmd)}")
                print(f"   Код ошибки: {result.returncode}")
                if result.stderr:
                    print(f"   Ошибка ffprobe: {result.stderr.strip()}")
                return []
            
            try:
                info = json.loads(result.stdout)
                total_duration = float(info['format']['duration'])
                print(f"⏱️ Общая длительность: {total_duration/60:.1f} минут")
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"❌ Ошибка парсинга информации о файле: {e}")
                print(f"   Вывод ffprobe: {result.stdout}")
                return []
            
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
                    if chunk_path.exists() and chunk_path.stat().st_size > 1000:  # Проверяем, что файл не пустой
                        chunk_paths.append(str(chunk_path))
                        print(f"✅ Создана часть {i+1}: {chunk_path.name}")
                    else:
                        if chunk_path.exists():
                            chunk_path.unlink()  # Удаляем пустой файл
                        print(f"⚠️ Часть {i+1} пуста или слишком мала")
                else:
                    print(f"❌ Ошибка создания части {i+1}")
                    print(f"   Команда: {' '.join(cmd)}")
                    print(f"   Код ошибки: {result.returncode}")
                    if result.stderr:
                        print(f"   Ошибка ffmpeg: {result.stderr.strip()}")
                    if result.stdout:
                        print(f"   Вывод ffmpeg: {result.stdout.strip()}")
            
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
