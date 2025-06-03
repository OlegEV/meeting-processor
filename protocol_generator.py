#!/usr/bin/env python3
"""
Модуль для генерации протоколов встреч через Claude API
"""

from typing import Dict, Optional

try:
    import anthropic
except ImportError:
    print("❌ Модуль anthropic не установлен: pip install anthropic")
    anthropic = None

class ProtocolGenerator:
    """Генератор протоколов встреч через Claude API"""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        if not anthropic:
            raise ImportError("anthropic не установлен")
            
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def generate_meeting_summary(self, 
                               transcript: str, 
                               file_datetime_info: Dict = None, 
                               template_type: str = "standard",
                               team_identification: Dict = None,
                               templates_system = None) -> Optional[str]:
        """Генерирует протокол встречи через Claude API"""
        try:
            print(f"🤖 Генерирую протокол встречи через Claude ({self.model})...")
            
            # Подготавливаем промпт
            if templates_system:
                # Используем систему шаблонов
                prompt = templates_system.get_template(template_type, transcript, file_datetime_info)
                prompt = prompt.format(transcript=transcript)
                print(f"📝 Используется шаблон: {template_type}")
                
                # Добавляем информацию о команде, если доступна
                if team_identification and team_identification.get("identified", False):
                    team_context = self._generate_team_context(team_identification, template_type)
                    prompt = f"{prompt}\n\n{team_context}"
                    print("👥 Добавлен контекст команды в промпт")
                
            else:
                # Встроенный шаблон
                prompt = self._generate_builtin_prompt(transcript, file_datetime_info, team_identification)
                print("📝 Используется встроенный стандартный шаблон")
            
            # Получаем настройки токенов
            max_tokens = 2000
            if templates_system and hasattr(templates_system, 'config'):
                max_tokens = templates_system.config.get("template_settings", {}).get("max_tokens", 2000)
            
            # Отправляем запрос к Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            summary = response.content[0].text
            
            # Добавляем техническую информацию
            summary = self._add_technical_info(
                summary, file_datetime_info, template_type, 
                team_identification, templates_system
            )
            
            print("✅ Протокол встречи создан")
            return summary
            
        except Exception as e:
            print(f"❌ Ошибка при создании протокола: {e}")
            return None
    
    def _generate_builtin_prompt(self, transcript: str, file_datetime_info: Dict = None, 
                               team_identification: Dict = None) -> str:
        """Генерирует встроенный промпт для Claude"""
        datetime_info = ""
        if file_datetime_info:
            datetime_info = f"""
Дата и время встречи: {file_datetime_info['date']} ({file_datetime_info['weekday_ru']}) в {file_datetime_info['time']}
"""
        
        team_info = ""
        if team_identification and team_identification.get("identified", False):
            team_info = f"\n\nИнформация о команде:\n{team_identification.get('participant_summary', '')}"
        
        return f"""
Проанализируй следующий транскрипт встречи и создай структурированный протокол.
{datetime_info}{team_info}
Транскрипт:
{transcript}

Пожалуйста, создай протокол встречи, включающий:

1. **Дата и время встречи**{f" - {file_datetime_info['datetime_full']}" if file_datetime_info else " - указать на основе контекста или как 'не указано'"}
2. **Участники встречи** - определи из транскрипта{' (учти предоставленную информацию о команде)' if team_identification else ''}
3. **Краткое резюме встречи**
4. **Основные обсуждаемые вопросы**
5. **Принятые решения**
6. **Назначенные задачи и ответственные**
7. **Следующие шаги**
8. **Дата следующей встречи (если упоминалась)**

Оформи ответ в структурированном виде с четкими заголовками.
Если дата и время не указаны в транскрипте, используй предоставленную информацию о файле.
"""
    
    def _generate_team_context(self, team_identification: Dict, template_type: str) -> str:
        """Генерирует контекст команды для добавления в промпт"""
        context_parts = []
        
        # Добавляем информацию об участниках
        participant_summary = team_identification.get("participant_summary", "")
        if participant_summary:
            context_parts.append("ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ О КОМАНДЕ:")
            context_parts.append(participant_summary)
        
        # Добавляем статистику
        stats = team_identification.get("statistics", {})
        if stats.get("teams_present"):
            teams_ru = {
                "management": "Руководство",
                "development": "Разработка", 
                "testing": "Тестирование",
                "analytics": "Аналитика"
            }
            teams_list = [teams_ru.get(team, team.title()) for team in stats["teams_present"]]
            context_parts.append(f"Представленные команды: {', '.join(teams_list)}")
        
        # Специфичные рекомендации для разных типов встреч
        if template_type == "standup":
            context_parts.append("При создании протокола стендапа группируй информацию по участникам и их командам.")
        elif template_type == "project": 
            context_parts.append("Учитывай роли участников при распределении задач и ответственности.")
        elif template_type == "review":
            context_parts.append("Структурируй обратную связь по командам и ролям участников.")
        
        return "\n".join(context_parts)
    
    def _add_technical_info(self, summary: str, file_datetime_info: Dict = None, 
                          template_type: str = None, team_identification: Dict = None,
                          templates_system = None) -> str:
        """Добавляет техническую информацию к протоколу"""
        # Проверяем, нужно ли добавлять техническую информацию
        include_tech_info = True
        if templates_system and hasattr(templates_system, 'config'):
            include_tech_info = templates_system.config.get("template_settings", {}).get("include_technical_info", True)
        
        if not include_tech_info:
            return summary
        
        technical_info = f"""

---
**ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ**
- Исходный файл обработан: {file_datetime_info['datetime_full'] if file_datetime_info else 'не указано'}
- День недели: {file_datetime_info['weekday_ru'] if file_datetime_info else 'не указано'}
- Тип шаблона: {template_type or 'standard'}
- Модель Claude: {self.model}
- Протокол создан автоматически на основе аудиозаписи"""
        
        # Добавляем информацию об идентификации команды
        if team_identification and team_identification.get("identified", False):
            stats = team_identification.get("statistics", {})
            avg_confidence = self._calculate_average_confidence(team_identification)
            technical_info += f"""
- Идентификация команды: ✅ включена
- Участников определено: {stats.get('total_identified', 0)}
- Команды на встрече: {', '.join(stats.get('teams_present', []))}
- Средняя точность определения: {avg_confidence:.0%}"""
        else:
            technical_info += f"""
- Идентификация команды: отключена или не применялась"""
        
        return summary + technical_info
    
    def _calculate_average_confidence(self, team_identification: Dict) -> float:
        """Вычисляет среднюю уверенность идентификации"""
        confidence_scores = team_identification.get("confidence_scores", {})
        if not confidence_scores:
            return 0.0
        
        return sum(confidence_scores.values()) / len(confidence_scores)