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
                       template_type: str, team_identification: Dict = None):
        """Сохраняет транскрипт с заголовком"""
        # Создаем заголовок транскрипта
        transcript_header = f"""ТРАНСКРИПТ ВСТРЕЧИ
Дата: {file_datetime_info['date']} ({file_datetime_info['weekday_ru']})
Время: {file_datetime_info['time']}
Файл: {Path(transcript_path).stem.replace('_transcript', '')}
Шаблон: {template_type}"""
        
        # Добавляем информацию о команде в заголовок
        if team_identification and team_identification.get("identified", False):
            stats = team_identification.get("statistics", {})
            avg_confidence = FileUtils._calculate_average_confidence(team_identification)
            transcript_header += f"""
Идентификация команды: ✅ Включена
Участников определено: {stats.get('total_identified', 0)}
Команды: {', '.join(stats.get('teams_present', []))}
Средняя точность: {avg_confidence:.0%}"""
        else:
            transcript_header += f"""
Идентификация команды: ❌ Отключена или не применялась"""
        
        transcript_with_header = f"{transcript_header}\n\n{'-' * 80}\n\n{transcript}"
        
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript_with_header)
        print(f"✅ Транскрипт сохранен: {transcript_path}")
    
    @staticmethod
    def save_team_info(team_info_path: str, team_identification: Dict, 
                      file_datetime_info: Dict, input_file_path: str, template_type: str):
        """Сохраняет подробную информацию о команде"""
        team_info_content = f"""ИНФОРМАЦИЯ О КОМАНДЕ
Дата: {file_datetime_info['date']} ({file_datetime_info['weekday_ru']})
Время: {file_datetime_info['time']}
Файл: {Path(input_file_path).name}
Шаблон: {template_type}

{team_identification.get('participant_summary', '')}

СТАТИСТИКА ИДЕНТИФИКАЦИИ:
- Всего участников определено: {team_identification['statistics']['total_identified']}
- Команды на встрече: {', '.join(team_identification['statistics']['teams_present'])}
- Средняя точность определения: {FileUtils._calculate_average_confidence(team_identification):.0%}

ДЕТАЛИЗАЦИЯ ПО УЧАСТНИКАМ:
"""
        
        # Добавляем детальную информацию о каждом участнике
        for speaker_id, member_info in team_identification.get('speakers', {}).items():
            confidence = team_identification.get('confidence_scores', {}).get(speaker_id, 0)
            team_info_content += f"""
{speaker_id}:
  - Имя: {member_info.get('full_name', 'неизвестно')}
  - Роль: {member_info.get('role', 'неизвестно')}
  - Команда: {member_info.get('team_name', 'неизвестно')}
  - Точность определения: {confidence:.0%}
"""
        
        team_info_content += f"""
ЗАМЕНЫ В ТРАНСКРИПТЕ:
"""
        for old_speaker, new_speaker in team_identification.get('replacements', {}).items():
            team_info_content += f"- {old_speaker} → {new_speaker}\n"
        
        with open(team_info_path, "w", encoding="utf-8") as f:
            f.write(team_info_content)
        print(f"✅ Информация о команде сохранена: {team_info_path}")
    
    @staticmethod
    def _calculate_average_confidence(team_identification: Dict) -> float:
        """Вычисляет среднюю уверенность идентификации"""
        confidence_scores = team_identification.get("confidence_scores", {})
        if not confidence_scores:
            return 0.0
        
        return sum(confidence_scores.values()) / len(confidence_scores)
    
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
