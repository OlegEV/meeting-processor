#!/usr/bin/env python3
"""
Тесты OpenRouterClient: управление режимом рассуждений (reasoning)
"""

import os
import sys
import unittest
from unittest.mock import Mock

import openai

# openai 3.x работает поверх httpx2, более ранние версии — поверх httpx
if int(openai.__version__.split('.')[0]) >= 3:
    import httpx2 as httpx
else:
    import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openrouter_client import OpenRouterClient, REASONING_DISABLED

MESSAGES = [{'role': 'user', 'content': 'Привет'}]

# Ошибка в том виде, в каком её возвращает прокси LiteLLM
MANDATORY_REASONING_ERROR = (
    'litellm.BadRequestError: OpenrouterException - {"error":{"message":"Reasoning is mandatory '
    'for this endpoint and cannot be disabled.","code":400,"metadata":{"provider_name":null}}}'
)


def bad_request(message: str) -> openai.BadRequestError:
    request = httpx.Request('POST', 'http://proxy.test/chat/completions')
    response = httpx.Response(400, request=request)
    return openai.BadRequestError(message, response=response, body={'error': {'message': message}})


def completion(content: str = 'Ответ', finish_reason: str = 'stop'):
    message = Mock(content=content, refusal=None, reasoning_content=None, reasoning=None, model_extra={})
    return Mock(choices=[Mock(message=message, finish_reason=finish_reason)], usage=None)


class TestOpenRouterReasoning(unittest.TestCase):
    """Отключение рассуждений и обход моделей, где оно запрещено"""

    def setUp(self):
        OpenRouterClient._reasoning_overrides.clear()
        self.addCleanup(OpenRouterClient._reasoning_overrides.clear)

    def make_client(self, model='anthropic/claude-sonnet-5.5', side_effect=None, **openrouter_config):
        client = OpenRouterClient('test_key', model, config={'openrouter': openrouter_config})
        client.client = Mock()
        client.client.chat.completions.create.side_effect = side_effect
        return client

    @staticmethod
    def sent_reasoning(client):
        return [call.kwargs['extra_body']['reasoning']
                for call in client.client.chat.completions.create.call_args_list]

    def test_client_is_configured_from_config(self):
        client = OpenRouterClient('test_key', 'anthropic/claude-sonnet-5.5', config={'openrouter': {
            'base_url': 'http://proxy.test:4000', 'timeout': 120.0, 'connect_timeout': 40.0, 'max_retries': 2
        }})

        self.assertEqual(str(client.client.base_url).rstrip('/'), 'http://proxy.test:4000')
        self.assertEqual(client.client.max_retries, 2)
        self.assertEqual(client.client.timeout.read, 120.0)
        self.assertEqual(client.client.timeout.connect, 40.0)

    def test_reasoning_is_disabled_by_default(self):
        client = self.make_client(model='openrouter/moonshotai/kimi-k3.1-pro', side_effect=[completion()])

        self.assertEqual(client.create_message(MESSAGES, max_tokens=100, temperature=0.2), 'Ответ')

        self.assertEqual(self.sent_reasoning(client), [REASONING_DISABLED])
        call = client.client.chat.completions.create.call_args
        self.assertEqual(call.kwargs['model'], 'openrouter/moonshotai/kimi-k3.1-pro')
        self.assertEqual(call.kwargs['max_tokens'], 100)
        self.assertEqual(call.kwargs['temperature'], 0.2)
        self.assertEqual(OpenRouterClient._reasoning_overrides, {})

    def test_mandatory_reasoning_is_retried_with_minimal_effort(self):
        client = self.make_client(side_effect=[bad_request(MANDATORY_REASONING_ERROR), completion('Протокол')])

        self.assertEqual(client.create_message(MESSAGES), 'Протокол')

        self.assertEqual(self.sent_reasoning(client),
                         [REASONING_DISABLED, {'effort': 'minimal', 'exclude': True}])

    def test_mandatory_reasoning_is_remembered_for_model(self):
        first = self.make_client(side_effect=[bad_request(MANDATORY_REASONING_ERROR), completion()])
        first.create_message(MESSAGES)

        # Новый экземпляр (следующая задача) не повторяет заведомо неудачный запрос
        second = self.make_client(side_effect=[completion('Второй')])
        self.assertEqual(second.create_message(MESSAGES), 'Второй')
        self.assertEqual(self.sent_reasoning(second), [{'effort': 'minimal', 'exclude': True}])

        # На другие модели это не влияет
        other = self.make_client(model='openrouter/deepseek/deepseek-v4-pro', side_effect=[completion()])
        other.create_message(MESSAGES)
        self.assertEqual(self.sent_reasoning(other), [REASONING_DISABLED])

    def test_falls_back_when_effort_is_rejected(self):
        client = self.make_client(side_effect=[
            bad_request(MANDATORY_REASONING_ERROR),
            bad_request('Unsupported parameter: reasoning.effort'),
            completion('Без effort'),
        ])

        self.assertEqual(client.create_message(MESSAGES), 'Без effort')

        self.assertEqual(self.sent_reasoning(client),
                         [REASONING_DISABLED, {'effort': 'minimal', 'exclude': True}, {'exclude': True}])
        self.assertEqual(OpenRouterClient._reasoning_overrides,
                         {'anthropic/claude-sonnet-5.5': {'exclude': True}})

    def test_effort_is_configurable(self):
        client = self.make_client(side_effect=[bad_request(MANDATORY_REASONING_ERROR), completion()],
                                  reasoning_effort='low')
        client.create_message(MESSAGES)
        self.assertEqual(self.sent_reasoning(client)[1], {'effort': 'low', 'exclude': True})

        OpenRouterClient._reasoning_overrides.clear()
        client = self.make_client(side_effect=[bad_request(MANDATORY_REASONING_ERROR), completion()],
                                  reasoning_effort=None)
        client.create_message(MESSAGES)
        self.assertEqual(self.sent_reasoning(client)[1], {'exclude': True})

    def test_other_bad_request_is_not_retried(self):
        client = self.make_client(side_effect=[bad_request('max_tokens is too large')])

        self.assertIsNone(client.create_message(MESSAGES))

        self.assertEqual(client.client.chat.completions.create.call_count, 1)
        self.assertEqual(OpenRouterClient._reasoning_overrides, {})

    def test_returns_none_when_all_variants_fail(self):
        client = self.make_client(side_effect=[
            bad_request(MANDATORY_REASONING_ERROR),
            bad_request('rejected'),
            bad_request('rejected again'),
        ])

        self.assertIsNone(client.create_message(MESSAGES))

        self.assertEqual(client.client.chat.completions.create.call_count, 3)
        self.assertEqual(OpenRouterClient._reasoning_overrides, {})


if __name__ == '__main__':
    unittest.main()
