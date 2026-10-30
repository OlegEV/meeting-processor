#!/usr/bin/env python3
"""
Утилиты для работы с файлами и метаданными
"""

import os
import datetime
from pathlib import Path
from typing import Dict

class FileUtils:
    """Утилиты для работы с файлами"""

    # Служебный заголовок файла транскрипта (см. save_transcript / strip_transcript_header)
    TRANSCRIPT_HEADER_MARKER = "ТРАНСКРИПТ ВСТРЕЧИ"
    TRANSCRIPT_HEADER_SEPARATOR = "-" * 80


    @staticmethod
    def get_file_datetime_info(file_path: str) -> Dict:
        """Получает информацию о дате и времени файла"""
        try:
            file_path = Path(file_path)
            stat = file_path.stat()
            
            # Время создания (Windows) или изменения статуса (Unix)
            if hasattr(stat, 'st_birthtime'):  # macOS
                creation_time = datetime.datetime.fromtimestamp(stat.st_birthtime)
            elif hasattr(stat, 'st_ctime'):  # Windows/Linux
                creation_time = datetime.datetime.fromtimestamp(stat.st_ctime)
            else:
                creation_time = None
            
            # Время последней модификации
            modification_time = datetime.datetime.fromtimestamp(stat.st_mtime)
            
            # Используем время создания, если доступно, иначе время модификации
            file_datetime = creation_time if creation_time else modification_time
            
            return {
                "datetime": file_datetime,
                "date": file_datetime.strftime("%d.%m.%Y"),
                "time": file_datetime.strftime("%H:%M:%S"),
                "datetime_full": file_datetime.strftime("%d.%m.%Y %H:%M:%S"),
                "weekday": file_datetime.strftime("%A"),
                "weekday_ru": FileUtils._get_russian_weekday(file_datetime.weekday()),
                "month_ru": FileUtils._get_russian_month(file_datetime.month)
            }
            
        except Exception as e:
            print(f"⚠️ Не удалось получить информацию о времени файла: {e}")
            now = datetime.datetime.now()
            return {
                "datetime": now,
                "date": now.strftime("%d.%m.%Y"),
                "time": now.strftime("%H:%M:%S"),
                "datetime_full": now.strftime("%d.%m.%Y %H:%M:%S"),
                "weekday": now.strftime("%A"),
                "weekday_ru": FileUtils._get_russian_weekday(now.weekday()),
                "month_ru": FileUtils._get_russian_month(now.month)
            }
    
    @staticmethod
    def _get_russian_weekday(weekday_index: int) -> str:
        """Возвращает название дня недели на русском"""
        weekdays = {
            0: "понедельник", 1: "вторник", 2: "среда", 3: "четверг",
            4: "пятница", 5: "суббота", 6: "воскресенье"
        }
        return weekdays.get(weekday_index, "неизвестно")
    
    @staticmethod
    def _get_russian_month(month_index: int) -> str:
        """Возвращает название месяца на русском"""
        months = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа", 
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        return months.get(month_index, "неизвестно")
    
    @staticmethod
    def save_transcript(transcript_path: str, transcript: str, file_datetime_info: Dict,
                       template_type: str):
        """Сохраняет транскрипт с заголовком"""
        transcript_header = f"""ТРАНСКРИПТ ВСТРЕЧИ
Дата: {file_datetime_info['date']} ({file_datetime_info['weekday_ru']})
Время: {file_datetime_info['time']}
Файл: {Path(transcript_path).stem.replace('_transcript', '')}
Шаблон: {template_type}"""

        transcript_with_header = f"{transcript_header}\n\n{'-' * 80}\n\n{transcript}"

        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript_with_header)
        print(f"✅ Транскрипт сохранен: {transcript_path}")

    @staticmethod
    def strip_transcript_header(transcript_text: str) -> str:
        """Убирает служебный заголовок, добавленный save_transcript.

        Нужно, чтобы в промпт уходила только речь участников: метаданные файла
        (дата, шаблон, статистика идентификации) не должны попадать в блок
        расшифровки и выглядеть для модели как факты встречи или инструкции.
        """
        if not transcript_text:
            return transcript_text

        if not transcript_text.lstrip().startswith(FileUtils.TRANSCRIPT_HEADER_MARKER):
            return transcript_text

        separator_position = transcript_text.find(FileUtils.TRANSCRIPT_HEADER_SEPARATOR)
        if separator_position == -1:
            return transcript_text

        body_start = separator_position + len(FileUtils.TRANSCRIPT_HEADER_SEPARATOR)
        return transcript_text[body_start:].lstrip("\n")

    @staticmethod
    def load_transcript(transcript_path: str) -> str:
        """Читает файл транскрипта без служебного заголовка"""
        with open(transcript_path, "r", encoding="utf-8") as f:
            return FileUtils.strip_transcript_header(f.read())

    @staticmethod
    def cleanup_temp_files(temp_audio_created: bool, audio_file_path: str, keep_audio_file: bool):
        """Очищает временные файлы"""
        if temp_audio_created and not keep_audio_file:
            try:
                os.remove(audio_file_path)
                print("🗑️ Временный аудиофайл удален")
            except:
                pass
        elif temp_audio_created and keep_audio_file:
            print(f"💾 Аудиофайл сохранен: {audio_file_path}")

    @staticmethod
    def cleanup_temp_dir(temp_dir: str):
        """Удаляет каталог temp_dir со всем содержимым (используется по завершении задачи)."""
        import shutil
        try:
            path = Path(temp_dir)
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            print(f"⚠️ Не удалось удалить временный каталог {temp_dir}: {e}")

    @staticmethod
    def cleanup_old_temp_entries(base_dir: str, max_age_seconds: int) -> int:
        """Удаляет содержимое base_dir старше max_age_seconds.

        Возвращает число удалённых записей верхнего уровня (файлов и подкаталогов).
        """
        import shutil
        import time

        base = Path(base_dir)
        if not base.exists():
            return 0

        cutoff = time.time() - max_age_seconds
        removed = 0
        for entry in base.iterdir():
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if mtime > cutoff:
                continue
            try:
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink()
                removed += 1
            except Exception as e:
                print(f"⚠️ Не удалось удалить {entry}: {e}")
        return removed
