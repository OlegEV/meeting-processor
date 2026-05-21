#!/usr/bin/env python3
"""
Клиент для работы с OpenRouter API
"""

import logging
from typing import Dict, Optional, List
import httpx
import openai

from config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """Клиент для работы с OpenRouter API"""
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-sonnet-4.5", config: Dict = None):
        """
        Инициализация клиента OpenRouter
        
        Args:
            api_key: API ключ OpenRouter
            model: Название модели (например, "anthropic/claude-sonnet-4.5")
            config: Словарь конфигурации (если None — загружается из config.json)
        """
        self.api_key = api_key
        self.model = model
        
        if config is None:
            config = ConfigLoader.load_config()
        
        or_cfg = config.get("openrouter", {})
        base_url      = or_cfg.get("base_url",       "https://openrouter.ai/api/v1")
        timeout        = or_cfg.get("timeout",        60.0)
        connect_timeout = or_cfg.get("connect_timeout", 30.0)
        max_retries    = or_cfg.get("max_retries",    3)
        
        # Настройка клиента OpenAI для работы с OpenRouter
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(timeout, connect=connect_timeout),
            max_retries=max_retries
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
                temperature=temperature,
                # Отключаем режим рассуждений для всех моделей (Kimi K2 thinking,
                # DeepSeek-R1, GPT-5, Claude extended thinking и т.п.), чтобы
                # экономить токены и получать ответ сразу в content.
                extra_body={"reasoning": {"enabled": False, "exclude": True}},
            )

            if not response.choices:
                logger.error(
                    "❌ OpenRouter вернул пустой список choices (модель %s)", self.model
                )
                print("❌ OpenRouter вернул пустой список choices")
                return None

            choice = response.choices[0]
            message = choice.message
            finish_reason = getattr(choice, "finish_reason", None)
            content = getattr(message, "content", None)

            # Некоторые модели (Kimi K2 thinking, DeepSeek-R1 и т.п.) кладут текст
            # в reasoning/reasoning_content, а content оставляют пустым. Берём оттуда
            # как запасной вариант, чтобы протокол всё-таки сгенерировался.
            if not (content and content.strip()):
                fallback = (
                    getattr(message, "reasoning_content", None)
                    or getattr(message, "reasoning", None)
                )
                # OpenAI SDK иногда хранит дополнительные поля в model_extra
                if not fallback:
                    extra = getattr(message, "model_extra", None) or {}
                    fallback = extra.get("reasoning_content") or extra.get("reasoning")

                refusal = getattr(message, "refusal", None)
                usage = getattr(response, "usage", None)
                logger.warning(
                    "⚠️ Пустой content от OpenRouter: model=%s finish_reason=%s "
                    "refusal=%s usage=%s fallback_found=%s",
                    self.model, finish_reason, refusal, usage, bool(fallback),
                )

                if fallback and fallback.strip():
                    logger.info(
                        "ℹ️ Использую reasoning_content в качестве ответа (%d симв.)",
                        len(fallback),
                    )
                    return fallback

                if finish_reason == "length":
                    logger.error(
                        "❌ Ответ обрезан по лимиту токенов (max_tokens=%s). "
                        "Увеличьте template_settings.max_tokens в templates_config.json.",
                        max_tokens,
                    )
                return None

            if finish_reason == "length":
                logger.warning(
                    "⚠️ Ответ модели %s обрезан по лимиту токенов (max_tokens=%s)",
                    self.model, max_tokens,
                )

            return content

        except Exception as e:
            logger.exception("❌ Ошибка при обращении к OpenRouter API: %s", e)
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