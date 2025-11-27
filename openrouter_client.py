#!/usr/bin/env python3
"""
Клиент для работы с OpenRouter API
"""

from typing import Dict, Optional, List
import openai

class OpenRouterClient:
    """Клиент для работы с OpenRouter API"""
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-sonnet-4.5"):
        """
        Инициализация клиента OpenRouter
        
        Args:
            api_key: API ключ OpenRouter
            model: Название модели (например, "anthropic/claude-sonnet-4.5")
        """
        self.api_key = api_key
        self.model = model
        
        # Настройка клиента OpenAI для работы с OpenRouter
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    
    def create_message(self, 
                      messages: List[Dict[str, str]], 
                      max_tokens: int = 2000,
                      temperature: float = 0.7) -> Optional[str]:
        """
        Создает сообщение через OpenRouter API
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}]
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура генерации (0.0 - 1.0)
            
        Returns:
            Текст ответа или None в случае ошибки
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ Ошибка при обращении к OpenRouter API: {e}")
            return None
    
    def create_message_anthropic_format(self, 
                                      content: str, 
                                      max_tokens: int = 2000) -> Optional[str]:
        """
        Создает сообщение в формате, совместимом с Anthropic API
        
        Args:
            content: Содержимое сообщения пользователя
            max_tokens: Максимальное количество токенов в ответе
            
        Returns:
            Текст ответа или None в случае ошибки
        """
        messages = [{"role": "user", "content": content}]
        return self.create_message(messages, max_tokens)
    
    @property
    def available_models(self) -> Dict[str, str]:
        """Возвращает доступные модели Anthropic через OpenRouter"""
        return {
            "claude-sonnet-4-20250514": "anthropic/claude-sonnet-4",
            "anthropic/claude-sonnet-4.5": "anthropic/claude-sonnet-4.5"
        }
    
    def get_openrouter_model_name(self, anthropic_model: str) -> str:
        """
        Преобразует название модели Anthropic в формат OpenRouter
        
        Args:
            anthropic_model: Название модели в формате Anthropic
            
        Returns:
            Название модели в формате OpenRouter
        """
        return self.available_models.get(anthropic_model, "anthropic/claude-sonnet-4.5")