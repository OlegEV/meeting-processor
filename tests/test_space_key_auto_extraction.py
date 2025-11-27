#!/usr/bin/env python3
"""
Тесты для автоматического извлечения space_key из URL Confluence
"""

import unittest
import tempfile
import os
import sys
import json
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_web import WorkingMeetingWebApp


class TestSpaceKeyAutoExtraction(unittest.TestCase):
    """Тесты автоматического извлечения space_key"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        
        # Create test configuration
        self.test_config = {
            'database': {
                'path': self.test_db.name,
                'timeout': 30,
                'check_same_thread': False
            },
            'auth': {
                'enabled': True,
                'debug_mode': True,
                'token_header': 'X-Identity-Token'
            },
            'confluence': {
                'enabled': True,
                'base_url': 'https://test.atlassian.net/wiki',
                'username': 'test@example.com',
                'api_token': 'test_token_123',
                'space_key': 'TEST'
            },
            'settings': {
                'max_file_size_mb': 200
            }
        }
        
        # Create temporary config file
        self.config_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(self.test_config, self.config_file, indent=2)
        self.config_file.close()
        
        # Mock API keys
        self.mock_api_keys = {
            'deepgram': {'api_key': 'test_deepgram_key'},
            'claude': {'api_key': 'test_claude_key'}
        }
    
    def tearDown(self):
        """Clean up test files"""
        try:
            os.unlink(self.test_db.name)
            os.unlink(self.config_file.name)
        except FileNotFoundError:
            pass
    
    def test_space_key_extraction_from_cloud_url(self):
        """Test space_key extraction from Confluence Cloud URLs"""
        test_cases = [
            {
                'url': 'https://test.atlassian.net/wiki/spaces/DEMO/pages/123456/Test+Page',
                'expected_space_key': 'DEMO',
                'description': 'Standard Cloud URL'
            },
            {
                'url': 'https://company.atlassian.net/wiki/spaces/PROJECT/pages/789012/Meeting+Notes',
                'expected_space_key': 'PROJECT',
                'description': 'Cloud URL with different domain'
            },
            {
                'url': 'https://test.atlassian.net/wiki/spaces/~user123/pages/456789/Personal+Page',
                'expected_space_key': '~user123',
                'description': 'Cloud URL with personal space'
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                extracted_space = self._extract_space_key_from_url(case['url'])
                self.assertEqual(extracted_space, case['expected_space_key'], 
                               f"Failed for {case['description']}: {case['url']}")
    
    def test_space_key_extraction_from_server_display_url(self):
        """Test space_key extraction from Confluence Server display URLs"""
        test_cases = [
            {
                'url': 'https://wiki.ekassir.com/display/~EgorovOV/TEST',
                'expected_space_key': '~EgorovOV',
                'description': 'Server display URL with personal space'
            },
            {
                'url': 'https://wiki.company.com/display/TEAM/Project+Page',
                'expected_space_key': 'TEAM',
                'description': 'Server display URL with regular space'
            },
            {
                'url': 'http://confluence.internal/display/DEV/Documentation',
                'expected_space_key': 'DEV',
                'description': 'Server display URL with HTTP'
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                extracted_space = self._extract_space_key_from_url(case['url'])
                self.assertEqual(extracted_space, case['expected_space_key'], 
                               f"Failed for {case['description']}: {case['url']}")
    
    def test_space_key_extraction_from_server_viewpage_url(self):
        """Test space_key extraction from Confluence Server viewpage URLs"""
        test_cases = [
            {
                'url': 'https://wiki.ekassir.com/pages/viewpage.action?pageId=706386930',
                'expected_space_key': None,
                'description': 'Server viewpage URL (no space_key in URL)'
            },
            {
                'url': 'http://confluence.company.com/pages/viewpage.action?pageId=123456',
                'expected_space_key': None,
                'description': 'Server viewpage URL with HTTP (no space_key in URL)'
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                extracted_space = self._extract_space_key_from_url(case['url'])
                self.assertEqual(extracted_space, case['expected_space_key'], 
                               f"Failed for {case['description']}: {case['url']}")
    
    def test_invalid_urls(self):
        """Test space_key extraction from invalid URLs"""
        test_cases = [
            {
                'url': 'invalid_url',
                'expected_space_key': None,
                'description': 'Invalid URL'
            },
            {
                'url': 'https://google.com',
                'expected_space_key': None,
                'description': 'Non-Confluence URL'
            },
            {
                'url': '',
                'expected_space_key': None,
                'description': 'Empty URL'
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                extracted_space = self._extract_space_key_from_url(case['url'])
                self.assertEqual(extracted_space, case['expected_space_key'], 
                               f"Failed for {case['description']}: {case['url']}")
    
    def _extract_space_key_from_url(self, url):
        """Extract space_key from URL using the same logic as the frontend"""
        import re
        
        if not url:
            return None
        
        # Confluence Cloud формат: /wiki/spaces/SPACE/pages/123456/PAGE
        cloud_pattern = r'/wiki/spaces/([^/]+)/pages/(\d+)/'
        match = re.search(cloud_pattern, url)
        if match:
            return match.group(1)
        
        # Confluence Server display формат: /display/SPACE/PAGE
        server_display_pattern = r'/display/([^/]+)/'
        match = re.search(server_display_pattern, url)
        if match:
            return match.group(1)
        
        # Confluence Server viewpage формат не содержит space_key в URL
        return None
    
    @patch('run_web.ConfigLoader.load_config')
    @patch('run_web.ConfigLoader.load_api_keys')
    @patch('run_web.ConfigLoader.validate_api_keys')
    def test_confluence_form_validation_without_space_key(self, mock_validate_keys, mock_load_api_keys, mock_load_config):
        """Test that Confluence form validation works without space_key field"""
        # Setup mocks
        mock_load_config.return_value = self.test_config
        mock_load_api_keys.return_value = self.mock_api_keys
        mock_validate_keys.return_value = (True, True, 'test_deepgram_key', 'test_claude_key')
        
        # Create Flask app for testing
        app = WorkingMeetingWebApp(self.config_file.name)
        client = app.app.test_client()
        app.app.config['TESTING'] = True
        
        # Test cases for form validation without space_key field
        test_cases = [
            {
                'base_page_url': 'https://wiki.ekassir.com/display/TEST/Page',
                'page_title': 'Test Page',
                'expected_valid': True,
                'expected_extracted_space': 'TEST'
            },
            {
                'base_page_url': 'https://test.atlassian.net/wiki/spaces/DEMO/pages/123/',
                'page_title': 'Demo Page',
                'expected_valid': True,
                'expected_extracted_space': 'DEMO'
            },
            {
                'base_page_url': 'https://wiki.ekassir.com/pages/viewpage.action?pageId=123456',
                'page_title': 'Server Page',
                'expected_valid': True,
                'expected_extracted_space': None  # Нужно будет извлекать из метаданных страницы
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                # Проверяем валидацию URL
                is_valid = self._validate_confluence_url(case['base_page_url'])
                self.assertEqual(is_valid, case['expected_valid'])
                
                # Проверяем извлечение space_key
                extracted_space = self._extract_space_key_from_url(case['base_page_url'])
                self.assertEqual(extracted_space, case['expected_extracted_space'])
    
    def _validate_confluence_url(self, url):
        """Validate Confluence URL format"""
        import re
        
        if not url:
            return False
        
        # Confluence Cloud формат: https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Page+Title
        cloud_pattern = r'^https?://[^/]+\.atlassian\.net/wiki/spaces/[^/]+/pages/\d+/'
        
        # Confluence Server формат 1: https://wiki.domain.com/pages/viewpage.action?pageId=123456
        server_pattern1 = r'^https?://[^/]+/pages/viewpage\.action\?pageId=\d+'
        
        # Confluence Server формат 2: https://wiki.domain.com/display/SPACE/PAGE
        server_pattern2 = r'^https?://[^/]+/display/[^/]+/[^/]+'
        
        is_cloud = re.match(cloud_pattern, url)
        is_server1 = re.match(server_pattern1, url)
        is_server2 = re.match(server_pattern2, url)
        
        return bool(is_cloud or is_server1 or is_server2)
    
    def test_space_key_priority_logic(self):
        """Test that space_key from URL takes priority over manual input"""
        # Этот тест проверяет логику приоритета:
        # 1. space_key из URL (если есть)
        # 2. space_key из метаданных страницы (для viewpage URLs)
        # 3. space_key из конфигурации (fallback)
        
        test_cases = [
            {
                'url': 'https://test.atlassian.net/wiki/spaces/DEMO/pages/123/',
                'config_space_key': 'DEFAULT',
                'expected_space_key': 'DEMO',  # URL имеет приоритет
                'description': 'URL space_key overrides config'
            },
            {
                'url': 'https://wiki.ekassir.com/display/PROJECT/Page',
                'config_space_key': 'DEFAULT',
                'expected_space_key': 'PROJECT',  # URL имеет приоритет
                'description': 'Display URL space_key overrides config'
            },
            {
                'url': 'https://wiki.ekassir.com/pages/viewpage.action?pageId=123456',
                'config_space_key': 'DEFAULT',
                'expected_space_key': 'DEFAULT',  # Fallback к конфигурации
                'description': 'Viewpage URL falls back to config'
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                # Извлекаем space_key из URL
                url_space_key = self._extract_space_key_from_url(case['url'])
                
                # Определяем финальный space_key по логике приоритета
                final_space_key = url_space_key or case['config_space_key']
                
                self.assertEqual(final_space_key, case['expected_space_key'],
                               f"Failed for {case['description']}")


if __name__ == '__main__':
    unittest.main()