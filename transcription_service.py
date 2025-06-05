#!/usr/bin/env python3
"""
Модуль для транскрипции аудио через Deepgram API
"""

import os
import time
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

try:
    from deepgram import DeepgramClient, PrerecordedOptions
except ImportError:
    print("❌ Модуль deepgram-sdk не установлен: pip install deepgram-sdk")
    DeepgramClient = None
    PrerecordedOptions = None

try:
    import httpx
except ImportError:
    print("⚠️ Модуль httpx не найден, используем стандартные таймауты")
    httpx = None

class TranscriptionService:
    """Сервис для транскрипции аудио через Deepgram"""
    
    def __init__(self, api_key: str, timeout: int = 300, options: dict = None, max_retries: int = 3):
        if not DeepgramClient:
            raise ImportError("deepgram-sdk не установлен")
            
        self.client = DeepgramClient(api_key)
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Настройки Deepgram по умолчанию
        default_options = {
            "punctuate": True,
            "diarize": True,
            "smart_format": True,
            "paragraphs": True,
            "utterances": False,
            "summarize": False,
            "detect_language": False
        }
        
        self.options = {**default_options, **(options or {})}
        # Принудительно включаем диаризацию для идентификации спикеров
        self.options["diarize"] = True
    
    def transcribe_audio_with_timeout(self, audio_data: bytes, timeout_override: Optional[int] = None) -> Optional[str]:
        """Транскрибирует аудио с настраиваемым таймаутом и retry при таймаутах"""
        timeout = timeout_override or self.timeout
        
        def transcribe_request():
            """Функция для выполнения запроса транскрипции"""
            # Создаем опции
            options = PrerecordedOptions(
                model="nova-2",
                language="ru",
                punctuate=self.options.get("punctuate", True),
                diarize=self.options.get("diarize", True),
                smart_format=self.options.get("smart_format", True),
                paragraphs=self.options.get("paragraphs", True),
                utterances=self.options.get("utterances", False),
                summarize=self.options.get("summarize", False),
                detect_language=self.options.get("detect_language", False)
            )
            
            payload = {"buffer": audio_data}
            response = self.client.listen.rest.v("1").transcribe_file(payload, options)
            
            # Анализируем структуру ответа
            channels = response.results.channels
            
            if channels and len(channels) > 0:
                alternatives = channels[0].alternatives
                
                if alternatives and len(alternatives) > 0:
                    transcript_data = alternatives[0]
                    
                    # Проверяем наличие различных данных
                    has_transcript = hasattr(transcript_data, 'transcript') and transcript_data.transcript
                    has_words = hasattr(transcript_data, 'words') and transcript_data.words
                    has_paragraphs = hasattr(transcript_data, 'paragraphs') and transcript_data.paragraphs
                    
                    if has_words:
                        words_with_speakers = [w for w in transcript_data.words if hasattr(w, 'speaker')]
                        
                        if words_with_speakers:
                            unique_speakers = set(getattr(w, 'speaker') for w in words_with_speakers)
                    
                    # Возвращаем отформатированный транскрипт
                    if has_words and self.options.get("diarize", True):
                        return self._format_transcript_with_speakers(transcript_data)
                    elif has_paragraphs and self.options.get("paragraphs", True):
                        return self._format_transcript_with_paragraphs(transcript_data)
                    else:
                        return transcript_data.transcript
            
            return "Ошибка: неожиданная структура ответа"
        
        # Retry логика при таймаутах
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt == 1:
                    print(f"🎤 Настройки Deepgram:")
                    print(f"   model: nova-2, language: ru")
                    for option, value in self.options.items():
                        print(f"   {option}: {value}")
                else:
                    print(f"🔄 Повторная попытка {attempt}/{self.max_retries}")
                
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(transcribe_request)
                    
                    try:
                        result = future.result(timeout=timeout)
                        if attempt > 1:
                            print(f"✅ Запрос успешен с попытки {attempt}")
                        else:
                            print(f"📊 Структура ответа Deepgram:")
                            channels = result.count("Спикер") if "Спикер" in result else 0
                            print(f"   Найдено спикеров: {channels}")
                        return result
                    except FutureTimeoutError:
                        print(f"⏰ Таймаут {timeout} секунд превышен (попытка {attempt}/{self.max_retries})")
                        future.cancel()
                        
                        # Если это не последняя попытка, ждем перед retry
                        if attempt < self.max_retries:
                            wait_time = min(10 * attempt, 30)  # Экспоненциальная задержка, максимум 30 сек
                            print(f"⏳ Ожидание {wait_time} секунд перед повтором...")
                            time.sleep(wait_time)
                        continue
                        
            except Exception as e:
                print(f"❌ Ошибка транскрипции (попытка {attempt}/{self.max_retries}): {e}")
                
                # Если это не последняя попытка, ждем перед retry
                if attempt < self.max_retries:
                    wait_time = min(5 * attempt, 15)  # Короткая задержка при других ошибках
                    print(f"⏳ Ожидание {wait_time} секунд перед повтором...")
                    time.sleep(wait_time)
                continue
        
        print(f"❌ Все {self.max_retries} попыток исчерпаны")
        return None
    
    def _format_transcript_with_paragraphs(self, transcript_data) -> str:
        """Форматирует транскрипт с параграфами"""
        try:
            if hasattr(transcript_data, 'paragraphs') and transcript_data.paragraphs:
                paragraphs = transcript_data.paragraphs.paragraphs
                formatted_paragraphs = []
                
                for i, paragraph in enumerate(paragraphs):
                    if hasattr(paragraph, 'sentences'):
                        sentences = [sentence.text for sentence in paragraph.sentences]
                        paragraph_text = ' '.join(sentences)
                        formatted_paragraphs.append(f"Параграф {i+1}:\n{paragraph_text}")
                    elif hasattr(paragraph, 'text'):
                        formatted_paragraphs.append(f"Параграф {i+1}:\n{paragraph.text}")
                
                if formatted_paragraphs:
                    print(f"📝 Отформатировано {len(formatted_paragraphs)} параграфов")
                    return '\n\n'.join(formatted_paragraphs)
            
            return transcript_data.transcript
            
        except Exception as e:
            print(f"⚠️ Ошибка форматирования параграфов: {e}")
            return transcript_data.transcript

    def _format_transcript_with_speakers(self, transcript_data) -> str:
        """Форматирует транскрипт с информацией о спикерах"""
        try:
            if not hasattr(transcript_data, 'words') or not transcript_data.words:
                return transcript_data.transcript
            
            # Группируем слова по спикерам и времени
            current_speaker = None
            current_segment = []
            segments = []
            
            for word in transcript_data.words:
                if hasattr(word, 'speaker'):
                    speaker = getattr(word, 'speaker')
                    word_text = getattr(word, 'word', '')
                    
                    if speaker != current_speaker:
                        # Сохраняем предыдущий сегмент
                        if current_segment and current_speaker is not None:
                            segments.append((current_speaker, ' '.join(current_segment)))
                        
                        # Начинаем новый сегмент
                        current_speaker = speaker
                        current_segment = [word_text]
                    else:
                        current_segment.append(word_text)
            
            # Добавляем последний сегмент
            if current_segment and current_speaker is not None:
                segments.append((current_speaker, ' '.join(current_segment)))
            
            # Форматируем результат
            if segments:
                formatted_segments = []
                for speaker, text in segments:
                    formatted_segments.append(f"Спикер {speaker}: {text}")
                
                result = '\n\n'.join(formatted_segments)
                print(f"📝 Отформатировано {len(segments)} сегментов с {len(set(s[0] for s in segments))} спикерами")
                return result
            else:
                return transcript_data.transcript
                
        except Exception as e:
            print(f"⚠️ Ошибка форматирования с спикерами: {e}")
            return transcript_data.transcript

    def transcribe_audio_chunks(self, chunk_paths: List[str], chunk_duration_minutes: int = 10) -> Optional[str]:
        """Транскрибирует список аудиофайлов и объединяет результаты"""
        try:
            print(f"🎤 Транскрибирую {len(chunk_paths)} частей...")
            
            full_transcript = []
            
            for i, chunk_path in enumerate(chunk_paths, 1):
                print(f"📝 Обрабатываю часть {i}/{len(chunk_paths)}: {Path(chunk_path).name}")
                
                try:
                    with open(chunk_path, "rb") as file:
                        buffer_data = file.read()
                    
                    transcript = self.transcribe_audio_with_timeout(
                        buffer_data, 
                        timeout_override=min(self.timeout, 180)
                    )
                    
                    if transcript and transcript.strip():
                        start_time = (i-1) * chunk_duration_minutes
                        end_time = i * chunk_duration_minutes
                        time_marker = f"\n\n=== ЧАСТЬ {i} ({start_time}:{end_time:02d} минут) ===\n"
                        full_transcript.append(time_marker + transcript)
                        print(f"✅ Часть {i} обработана ({len(transcript)} символов)")
                    else:
                        print(f"⚠️ Часть {i} пуста или не распознана")
                        
                except Exception as e:
                    print(f"❌ Ошибка транскрипции части {i}: {e}")
                    continue
                
                # Удаляем временный файл части
                try:
                    os.remove(chunk_path)
                except:
                    pass
                
                # Пауза между запросами
                if i < len(chunk_paths):
                    print("⏳ Пауза 5 секунд...")
                    time.sleep(5)
            
            if full_transcript:
                combined_transcript = "\n".join(full_transcript)
                print(f"✅ Все части обработаны. Общий размер: {len(combined_transcript)} символов")
                return combined_transcript
            else:
                print("❌ Не удалось получить транскрипт ни одной части")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при транскрипции частей: {e}")
            return None

    def transcribe_audio(self, audio_path: str, chunk_duration_minutes: int = 10) -> Optional[str]:
        """Транскрибирует аудио файл"""
        try:
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"📊 Размер аудиофайла: {file_size_mb:.1f} MB")
            
            # Получаем длительность файла
            import subprocess
            import json
            
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                duration_minutes = float(info['format']['duration']) / 60
                print(f"⏱️ Длительность: {duration_minutes:.1f} минут")
                
                # Разбиваем файл на части, если он слишком большой или длинный
                if duration_minutes > 15 or file_size_mb > 25:
                    print("🔪 Файл слишком длинный/большой, разбиваю на части...")
                    from audio_processor import AudioProcessor
                    audio_proc = AudioProcessor()
                    chunk_paths = audio_proc.split_audio_file(audio_path, chunk_duration_minutes)
                    
                    if chunk_paths:
                        return self.transcribe_audio_chunks(chunk_paths, chunk_duration_minutes)
                    else:
                        print("❌ Не удалось разбить файл")
                        return None
            
            print("🎤 Транскрибирю аудио через Deepgram...")
            
            with open(audio_path, "rb") as file:
                buffer_data = file.read()
            
            transcript = self.transcribe_audio_with_timeout(buffer_data)
            
            if transcript:
                print("✅ Транскрипция завершена")
                return transcript
            else:
                print("❌ Не удалось транскрибировать файл")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при транскрипции: {e}")
            return None
