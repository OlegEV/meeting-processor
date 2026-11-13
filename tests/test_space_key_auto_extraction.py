#!/usr/bin/env python3
"""
Тесты для автоматического извлечения space_key и page_id из URL Confluence
(WorkingMeetingWebApp.extract_confluence_metadata)
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch

import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_web import WorkingMeetingWebApp


def extract(url, api_token=None):
    """Вызывает extract_confluence_metadata; метод не использует состояние приложения"""
    return WorkingMeetingWebApp.extract_confluence_metadata(None, url, api_token, timeout=5)


def http_response(status_code=200, text='', json_data=None):
    response = Mock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_data or {}
    return response


class TestSpaceKeyAutoExtraction(unittest.TestCase):
    """Тесты автоматического извлечения метаданных страницы Confluence"""

    def setUp(self):
        # Сеть в тестах недоступна: любой HTTP-запрос завершается ошибкой соединения,
        # если тест явно не подменил ответ
        offline = requests.ConnectionError('network is disabled in tests')
        self.mock_get = patch('requests.get', side_effect=offline).start()
        self.mock_session_get = patch('requests.Session.get', side_effect=offline).start()
        self.addCleanup(patch.stopall)

    def test_empty_url(self):
        """Пустой URL не даёт метаданных и не вызывает запросов"""
        result = extract('')

        self.assertIsNone(result['page_id'])
        self.assertIsNone(result['space_key'])
        self.assertEqual(result['extraction_method'], 'none')
        self.mock_get.assert_not_called()
        self.mock_session_get.assert_not_called()

    def test_cloud_url(self):
        """Из Cloud URL извлекаются space_key и page_id без обращения к сети"""
        test_cases = [
            ('https://test.atlassian.net/wiki/spaces/DEMO/pages/123456/Test+Page', 'DEMO', '123456'),
            ('https://company.atlassian.net/wiki/spaces/PROJECT/pages/789012/Meeting+Notes', 'PROJECT', '789012'),
            ('https://test.atlassian.net/wiki/spaces/~user123/pages/456789/Personal+Page', '~user123', '456789'),
        ]

        for url, space_key, page_id in test_cases:
            with self.subTest(url=url):
                result = extract(url)

                self.assertEqual(result['space_key'], space_key)
                self.assertEqual(result['page_id'], page_id)
                self.assertEqual(result['extraction_method'], 'url_cloud')

        self.mock_get.assert_not_called()
        self.mock_session_get.assert_not_called()

    def test_server_display_url(self):
        """Из Server display URL извлекается space_key"""
        test_cases = [
            ('https://wiki.example.com/display/~IvanovII/TEST', '~IvanovII'),
            ('https://wiki.company.com/display/TEAM/Project+Page', 'TEAM'),
            ('https://confluence.example.org/display/DEV/API+Documentation', 'DEV'),
        ]

        for url, space_key in test_cases:
            with self.subTest(url=url):
                result = extract(url)

                self.assertEqual(result['space_key'], space_key)
                self.assertEqual(result['base_url'], url.split('/display/')[0])
                self.assertEqual(result['extraction_method'], 'url_display')

    def test_server_display_url_resolves_page_id_via_rest_api(self):
        """При наличии токена page_id страницы display URL запрашивается через REST API"""
        self.mock_get.side_effect = None
        self.mock_get.return_value = http_response(json_data={
            'results': [{'id': 987654, 'title': 'Project Page'}]
        })

        result = extract('https://wiki.company.com/display/TEAM/Project+Page', api_token='token')

        self.assertEqual(result['space_key'], 'TEAM')
        self.assertEqual(result['page_id'], '987654')
        self.assertEqual(result['page_title'], 'Project Page')
        self.assertEqual(result['extraction_method'], 'rest_api')

        call = self.mock_get.call_args
        self.assertEqual(call.args[0], 'https://wiki.company.com/rest/api/content')
        self.assertEqual(call.kwargs['params']['spaceKey'], 'TEAM')
        self.assertEqual(call.kwargs['params']['title'], 'Project Page')
        self.assertEqual(call.kwargs['headers']['Authorization'], 'Bearer token')

    def test_server_viewpage_url(self):
        """Из Server viewpage URL извлекается page_id; space_key в URL отсутствует"""
        result = extract('https://wiki.example.com/pages/viewpage.action?pageId=123456')

        self.assertEqual(result['page_id'], '123456')
        self.assertIsNone(result['space_key'])
        self.assertEqual(result['extraction_method'], 'url_viewpage')

    def test_server_viewpage_url_reads_space_key_from_page_html(self):
        """Для viewpage URL space_key берётся из метаданных HTML-страницы"""
        html = (
            '<html><head><title>Parent page - Confluence</title>'
            '<meta name="ajs-page-id" content="123456">'
            '<meta name="ajs-space-key" content="TEAM">'
            '</head></html>'
        )
        self.mock_session_get.side_effect = None
        self.mock_session_get.return_value = http_response(text=html)

        result = extract('https://wiki.example.com/pages/viewpage.action?pageId=123456', api_token='token')

        self.assertEqual(result['page_id'], '123456')
        self.assertEqual(result['space_key'], 'TEAM')
        self.assertEqual(result['page_title'], 'Parent page')
        self.assertEqual(result['extraction_method'], 'html_metadata')

    def test_unsupported_urls(self):
        """URL, не похожие на страницу Confluence, не дают space_key и page_id"""
        for url in ('https://example.com/some/page',
                    'not-a-url',
                    'https://wiki.example.com/spaces/TEST/overview'):
            with self.subTest(url=url):
                result = extract(url)

                self.assertIsNone(result['space_key'])
                self.assertIsNone(result['page_id'])


if __name__ == '__main__':
    unittest.main()
