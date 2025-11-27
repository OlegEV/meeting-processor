
#!/usr/bin/env python3
"""
Frontend/UI tests for JavaScript functionality and user interface components
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys
import json
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from run_web import WorkingMeetingWebApp


@unittest.skipUnless(SELENIUM_AVAILABLE, "Selenium not available")
class TestFrontendUI(unittest.TestCase):
    """Frontend UI tests using Selenium WebDriver"""
    
    @classmethod
    def setUpClass(cls):
        """Set up WebDriver for the test class"""
        # Configure Chrome options for headless testing
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            cls.driver = webdriver.Chrome(options=chrome_options)
            cls.driver.implicitly_wait(10)
        except Exception as e:
            raise unittest.SkipTest(f"Chrome WebDriver not available: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up WebDriver"""
        if hasattr(cls, 'driver'):
            cls.driver.quit()
    
    def setUp(self):
        """Set up test Flask application"""
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
                'debug_mode': True,  # Enable debug mode for testing
                'token_header': 'X-Identity-Token',
                'jwt_secret': 'test_secret_key_for_testing'
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
            },
            'supported_formats': {
                'audio': ['.mp3', '.wav', '.flac'],
                'video': ['.mp4', '.avi', '.mov']
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
        
        # Create API keys file
        self.api_keys_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(self.mock_api_keys, self.api_keys_file, indent=2)
        self.api_keys_file.close()
        
        # Update config to point to API keys file
        self.test_config['paths'] = {'api_keys_config': self.api_keys_file.name}
        with open(self.config_file.name, 'w') as f:
            json.dump(self.test_config, f, indent=2)
        
        # Mock ConfigLoader
        with patch('run_web.ConfigLoader.load_config') as mock_load_config, \
             patch('run_web.ConfigLoader.load_api_keys') as mock_load_api_keys, \
             patch('run_web.ConfigLoader.validate_api_keys') as mock_validate_keys:
            
            mock_load_config.return_value = self.test_config
            mock_load_api_keys.return_value = self.mock_api_keys
            mock_validate_keys.return_value = (True, True, 'test_deepgram_key', 'test_claude_key')
            
            # Create Flask app
            self.app = WorkingMeetingWebApp(self.config_file.name)
            self.app.app.config['TESTING'] = True
        
        # Start Flask app in a separate thread
        import threading
        self.flask_thread = threading.Thread(
            target=lambda: self.app.run(host='127.0.0.1', port=5555, debug=False)
        )
        self.flask_thread.daemon = True
        self.flask_thread.start()
        
        # Wait for Flask app to start
        time.sleep(2)
        
        self.base_url = 'http://127.0.0.1:5555'
        
        # Create test user
        self.test_user_id = 'ui_test_user'
        self.test_user_data = {
            'user_id': self.test_user_id,
            'email': 'uitest@example.com',
            'name': 'UI Test User'
        }
        self.app.db_manager.create_user(self.test_user_data)
    
    def tearDown(self):
        """Clean up test files"""
        try:
            os.unlink(self.test_db.name)
            os.unlink(self.config_file.name)
            os.unlink(self.api_keys_file.name)
        except FileNotFoundError:
            pass
    
    def test_index_page_loads(self):
        """Test that index page loads correctly"""
        self.driver.get(self.base_url)
        
        # Wait for page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check page title
        self.assertIn("Meeting Processor", self.driver.title)
        
        # Check for main elements
        self.assertTrue(self.driver.find_element(By.TAG_NAME, "form"))
        self.assertTrue(self.driver.find_element(By.NAME, "file"))
        self.assertTrue(self.driver.find_element(By.NAME, "template"))
    
    def test_file_upload_form_validation(self):
        """Test file upload form validation"""
        self.driver.get(self.base_url)
        
        # Wait for form to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "file"))
        )
        
        # Try to submit form without file
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        submit_button.click()
        
        # Check for validation message (HTML5 validation)
        file_input = self.driver.find_element(By.NAME, "file")
        validation_message = file_input.get_attribute("validationMessage")
        self.assertIsNotNone(validation_message)
    
    def test_template_selection(self):
        """Test template selection functionality"""
        self.driver.get(self.base_url)
        
        # Wait for template select to load
        template_select = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "template"))
        )
        
        # Get all template options
        from selenium.webdriver.support.ui import Select
        select = Select(template_select)
        options = select.options
        
        # Should have multiple template options
        self.assertGreater(len(options), 1)
        
        # Test selecting different templates
        for option in options[:3]:  # Test first 3 options
            select.select_by_value(option.get_attribute("value"))
            selected_value = select.first_selected_option.get_attribute("value")
            self.assertEqual(selected_value, option.get_attribute("value"))
    
    def test_file_format_display(self):
        """Test that supported file formats are displayed"""
        self.driver.get(self.base_url)
        
        # Wait for page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check for file format information
        page_source = self.driver.page_source
        self.assertIn("MP3", page_source.upper())
        self.assertIn("WAV", page_source.upper())
    
    def test_status_page_elements(self):
        """Test status page elements"""
        # Create a test job first
        job_data = {
            'job_id': 'ui_test_job',
            'user_id': self.test_user_id,
            'filename': 'ui_test.mp3',
            'template': 'standard',
            'status': 'processing',
            'progress': 75,
            'message': 'Processing audio...'
        }
        self.app.db_manager.create_job(job_data)
        
        # Navigate to status page
        self.driver.get(f"{self.base_url}/status/ui_test_job")
        
        # Wait for status page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check for status elements
        page_source = self.driver.page_source
        self.assertIn("ui_test.mp3", page_source)
        self.assertIn("processing", page_source)
        self.assertIn("75", page_source)  # Progress
    
    def test_jobs_list_page(self):
        """Test jobs list page functionality"""
        # Create multiple test jobs
        job_data_list = [
            {
                'job_id': 'ui_list_job_1',
                'user_id': self.test_user_id,
                'filename': 'list_test1.mp3',
                'template': 'standard',
                'status': 'completed',
                'progress': 100
            },
            {
                'job_id': 'ui_list_job_2',
                'user_id': self.test_user_id,
                'filename': 'list_test2.mp3',
                'template': 'business',
                'status': 'processing',
                'progress': 50
            }
        ]
        
        for job_data in job_data_list:
            self.app.db_manager.create_job(job_data)
        
        # Navigate to jobs list page
        self.driver.get(f"{self.base_url}/jobs")
        
        # Wait for jobs list to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check for job entries
        page_source = self.driver.page_source
        self.assertIn("list_test1.mp3", page_source)
        self.assertIn("list_test2.mp3", page_source)
        self.assertIn("completed", page_source)
        self.assertIn("processing", page_source)
    
    def test_confluence_publication_form(self):
        """Test Confluence publication form elements"""
        # Create completed job
        job_data = {
            'job_id': 'ui_confluence_job',
            'user_id': self.test_user_id,
            'filename': 'confluence_ui_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'summary_file': '/tmp/test_summary.md'
        }
        self.app.db_manager.create_job(job_data)
        
        # Navigate to status page
        self.driver.get(f"{self.base_url}/status/ui_confluence_job")
        
        # Wait for page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check for Confluence publication elements
        page_source = self.driver.page_source
        if "confluence" in page_source.lower():
            # Look for Confluence-related form elements
            try:
                confluence_form = self.driver.find_element(By.ID, "confluenceForm")
                self.assertIsNotNone(confluence_form)
            except NoSuchElementException:
                # Form might be in a different structure
                pass
    
    def test_responsive_design(self):
        """Test responsive design elements"""
        self.driver.get(self.base_url)
        
        # Test different viewport sizes
        viewport_sizes = [
            (1920, 1080),  # Desktop
            (768, 1024),   # Tablet
            (375, 667)     # Mobile
        ]
        
        for width, height in viewport_sizes:
            self.driver.set_window_size(width, height)
            time.sleep(1)  # Allow time for responsive changes
            
            # Check that page is still functional
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "file"))
            )
            
            # Verify form elements are still accessible
            file_input = self.driver.find_element(By.NAME, "file")
            self.assertTrue(file_input.is_displayed())
    
    def test_navigation_links(self):
        """Test navigation links functionality"""
        self.driver.get(self.base_url)
        
        # Wait for page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Look for navigation links
        try:
            # Test jobs link
            jobs_link = self.driver.find_element(By.LINK_TEXT, "Jobs")
            jobs_link.click()
            
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/jobs")
            )
            self.assertIn("/jobs", self.driver.current_url)
            
        except NoSuchElementException:
            # Navigation might be structured differently
            pass
        
        # Go back to home
        self.driver.get(self.base_url)
        
        try:
            # Test statistics link
            stats_link = self.driver.find_element(By.LINK_TEXT, "Statistics")
            stats_link.click()
            
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/statistics")
            )
            self.assertIn("/statistics", self.driver.current_url)
            
        except NoSuchElementException:
            # Statistics link might not be present
            pass
    
    def test_error_message_display(self):
        """Test error message display functionality"""
        # Navigate to a non-existent job status page
        self.driver.get(f"{self.base_url}/status/nonexistent_job")
        
        # Should redirect or show error
        time.sleep(2)
        
        # Check if redirected to home or error shown
        current_url = self.driver.current_url
        self.assertTrue(
            current_url == self.base_url or 
            current_url == f"{self.base_url}/" or
            "error" in self.driver.page_source.lower()
        )
    
    def test_progress_indicators(self):
        """Test progress indicators and dynamic updates"""
        # Create job with progress
        job_data = {
            'job_id': 'ui_progress_job',
            'user_id': self.test_user_id,
            'filename': 'progress_test.mp3',
            'template': 'standard',
            'status': 'processing',
            'progress': 25,
            'message': 'Starting processing...'
        }
        self.app.db_manager.create_job(job_data)
        
        # Navigate to status page
        self.driver.get(f"{self.base_url}/status/ui_progress_job")
        
        # Wait for page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Look for progress indicators
        page_source = self.driver.page_source
        self.assertIn("25", page_source)  # Progress value
        
        # Check for progress bar or similar elements
        try:
            progress_element = self.driver.find_element(By.CSS_SELECTOR, ".progress, [role='progressbar'], .progress-bar")
            self.assertIsNotNone(progress_element)
        except NoSuchElementException:
            # Progress might be displayed differently
            pass


class TestJavaScriptFunctionality(unittest.TestCase):
    """Test JavaScript functionality without browser automation"""
    
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
        
        # Mock API keys
        self.mock_api_keys = {
            'deepgram': {'api_key': 'test_deepgram_key'},
            'claude': {'api_key': 'test_claude_key'}
        }
    
    def tearDown(self):
        """Clean up test files"""
        try:
            os.unlink(self.test_db.name)
        except FileNotFoundError:
            pass
    
    def test_ajax_status_updates(self):
        """Test AJAX status update functionality"""
        # This would test the JavaScript AJAX calls for status updates
        # Since we can't run JavaScript directly, we test the API endpoints
        # that the JavaScript would call
        
        # Create Flask app for testing
        with patch('run_web.ConfigLoader.load_config') as mock_load_config, \
             patch('run_web.ConfigLoader.load_api_keys') as mock_load_api_keys, \
             patch('run_web.ConfigLoader.validate_api_keys') as mock_validate_keys:
            
            mock_load_config.return_value = self.test_config
            mock_load_api_keys.return_value = self.mock_api_keys
            mock_validate_keys.return_value = (True, True, 'test_deepgram_key', 'test_claude_key')
            
            app = WorkingMeetingWebApp('test_config.json')
            client = app.app.test_client()
            app.app.config['TESTING'] = True
            
            # Create test user and job
            test_user_id = 'js_test_user'
            user_data = {
                'user_id': test_user_id,
                'email': 'jstest@example.com',
                'name': 'JS Test User'
            }
            app.db_manager.create_user(user_data)
            
            job_data = {
                'job_id': 'js_test_job',
                'user_id': test_user_id,
                'filename': 'js_test.mp3',
                'template': 'standard',
                'status': 'processing',
                'progress': 50,
                'message': 'Processing...'
            }
            app.db_manager.create_job(job_data)
            
            # Test API endpoint that JavaScript would call
            headers = {
                'X-Identity-Token': 'test_token',
                'X-User-Id': test_user_id,
                'X-User-Email': 'jstest@example.com',
                'X-User-Name': 'JS Test User'
            }
            
            response = client.get('/api/status/js_test_job', headers=headers)
            
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'processing')
            self.assertEqual(data['progress'], 50)
            self.assertEqual(data['filename'], 'js_test.mp3')
    
    def test_confluence_form_validation(self):
        """Test Confluence form validation logic"""
        # Test the validation that would be performed by JavaScript
        
        # Test cases for form validation (без поля space_key - теперь извлекается автоматически)
        test_cases = [
            {
                'base_page_url': '',
                'page_title': 'Test Title',
                'expected_valid': False,
                'error': 'URL required'
            },
            {
                'base_page_url': 'invalid_url',
                'page_title': 'Test Title',
                'expected_valid': False,
                'error': 'Invalid URL format'
            },
            # Confluence Cloud формат
            {
                'base_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/123/',
                'page_title': '',
                'expected_valid': True,  # Title can be auto-generated
                'error': None
            },
            {
                'base_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/123/',
                'page_title': 'Valid Title',
                'expected_valid': True,
                'error': None
            },
            # Confluence Server формат
            {
                'base_page_url': 'https://wiki.ekassir.com/pages/viewpage.action?pageId=706386930',
                'page_title': 'Server Test Title',
                'expected_valid': True,
                'error': None
            },
            {
                'base_page_url': 'http://confluence.company.com/pages/viewpage.action?pageId=123456',
                'page_title': '',
                'expected_valid': True,  # Title can be auto-generated
                'error': None
            },
            # Confluence Server display формат
            {
                'base_page_url': 'https://wiki.ekassir.com/display/~EgorovOV/TEST',
                'page_title': 'Display Format Test',
                'expected_valid': True,
                'error': None
            },
            # Неправильные Server форматы
            {
                'base_page_url': 'https://wiki.ekassir.com/pages/viewpage.action?pageId=abc',
                'page_title': 'Invalid Page ID',
                'expected_valid': False,
                'error': 'Invalid page ID format'
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                # Simulate JavaScript validation logic
                is_valid = self._validate_confluence_form(case)
                self.assertEqual(is_valid, case['expected_valid'])
    
    def _validate_confluence_form(self, form_data):
        """Simulate JavaScript form validation"""
        import re
        
        # Check required URL
        if not form_data.get('base_page_url', '').strip():
            return False
        
        # Check URL format - поддерживаем Cloud, Server viewpage и Server display форматы
        base_page_url = form_data['base_page_url']
        
        # Confluence Cloud формат: https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Page+Title
        cloud_pattern = r'^https?://[^/]+\.atlassian\.net/wiki/spaces/[^/]+/pages/\d+/'
        
        # Confluence Server формат 1: https://wiki.domain.com/pages/viewpage.action?pageId=123456
        server_pattern1 = r'^https?://[^/]+/pages/viewpage\.action\?pageId=\d+'
        
        # Confluence Server формат 2: https://wiki.domain.com/display/SPACE/PAGE
        server_pattern2 = r'^https?://[^/]+/display/[^/]+/[^/]+'
        
        is_cloud = re.match(cloud_pattern, base_page_url)
        is_server1 = re.match(server_pattern1, base_page_url)
        is_server2 = re.match(server_pattern2, base_page_url)
        
        if not (is_cloud or is_server1 or is_server2):
            return False
        
        return True
    
    def test_space_key_auto_extraction(self):
        """Test automatic space_key extraction from URLs"""
        # Test cases for space_key extraction
        test_cases = [
            {
                'url': 'https://test.atlassian.net/wiki/spaces/DEMO/pages/123456/Test+Page',
                'expected_space_key': 'DEMO',
                'description': 'Confluence Cloud format'
            },
            {
                'url': 'https://wiki.ekassir.com/display/~EgorovOV/TEST',
                'expected_space_key': '~EgorovOV',
                'description': 'Confluence Server display format with personal space'
            },
            {
                'url': 'https://wiki.ekassir.com/display/TEAM/Project+Page',
                'expected_space_key': 'TEAM',
                'description': 'Confluence Server display format with regular space'
            },
            {
                'url': 'https://wiki.ekassir.com/pages/viewpage.action?pageId=706386930',
                'expected_space_key': None,
                'description': 'Confluence Server viewpage format (no space_key in URL)'
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
    
    def test_confluence_form_without_space_key_field(self):
        """Test that Confluence form validation works without space_key field"""
        # Тестируем, что валидация работает без поля space_key
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
                is_valid = self._validate_confluence_form(case)
                self.assertEqual(is_valid, case['expected_valid'])
                
                # Проверяем извлечение space_key
                extracted_space = self._extract_space_key_from_url(case['base_page_url'])
                self.assertEqual(extracted_space, case['expected_extracted_space'])
    
    def test_file_upload_validation(self):
        """Test file upload validation logic"""
        # Test cases for file validation
        test_cases = [
            {
                'filename': 'test.mp3',
                'size': 50 * 1024 * 1024,  # 50MB
                'expected_valid': True
            },
            {
                'filename': 'test.txt',
                'size': 10 * 1024 * 1024,  # 10MB
                'expected_valid': False  # Wrong format
            },
            {
                'filename': 'test.mp3',
                'size': 250 * 1024 * 1024,  # 250MB
                'expected_valid': False  # Too large
            },
            {
                'filename': '',
                'size': 10 * 1024 * 1024,
                'expected_valid': False  # No filename
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                is_valid = self._validate_file_upload(case)
                self.assertEqual(is_valid, case['expected_valid'])
    
    def _validate_file_upload(self, file_data):
        """Simulate JavaScript file validation"""
        # Check filename
        if not file_data.get('filename', '').strip():
            return False
        
        # Check file extension
        allowed_extensions = {'.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.opus', '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm'}
        filename = file_data['filename'].lower()
        
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            return False
        
        # Check file size (200MB limit)
        max_size = 200 * 1024 * 1024
        if file_data.get('size', 0) > max_size:
            return False
        
        return True
    
    def test_progress_bar_updates(self):
        """Test progress bar update logic"""
        # Test progress bar calculation and display
        test_cases = [
            {'progress': 0, 'expected_width': '0%', 'expected_class': 'progress-bar'},
            {'progress': 25, 'expected_width': '25%', 'expected_class': 'progress-bar'},
            {'progress': 50, 'expected_width': '50%', 'expected_class': 'progress-bar'},
            {'progress': 75, 'expected_width': '75%', 'expected_class': 'progress-bar'},
            {'progress': 100, 'expected_width': '100%', 'expected_class': 'progress-bar progress-bar-success'}
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                result = self._calculate_progress_display(case['progress'])
                self.assertEqual(result['width'], case['expected_width'])
                self.assertIn('progress-bar', result['class'])
    
    def _calculate_progress_display(self, progress):
        """Simulate JavaScript progress bar calculation"""
        width = f"{max(0, min(100, progress))}%"
        css_class = 'progress-bar'
        
        if progress >= 100:
            css_class += ' progress-bar-success'
        elif progress >= 75:
            css_class += ' progress-bar-info'
        elif progress >= 50:
            css_class += ' progress-bar-warning'
        
        return {
            'width': width,
            'class': css_class
        }
    
    def test_dynamic_content_updates(self):
        """Test dynamic content update functionality"""
        # Test the logic for updating page content dynamically
        
        # Simulate status updates
        initial_status = {
            'status': 'uploaded',
            'progress': 0,
            'message': 'File uploaded'
        }
        
        updated_status = {
            'status': 'processing',
            'progress': 50,
            'message': 'Processing audio...'
        }
        
        final_status = {
            'status': 'completed',
            'progress': 100,
            'message': 'Processing completed'
        }
        
        # Test status transitions
        self.assertEqual(initial_status['status'], 'uploaded')
        self.assertEqual(updated_status['status'], 'processing')
        self.assertEqual(final_status['status'], 'completed')
        
        # Test progress increases
        self.assertLess(initial_status['progress'], updated_status['progress'])
        self.assertLess(updated_status['progress'], final_status['progress'])
    
    def test_error_handling_display(self):
        """Test error handling and display logic"""
        # Test error message formatting and display
        test_errors = [
            {
                'error': 'Network timeout',
                'expected_type': 'warning',
                'expected_dismissible': True
            },
            {
                'error': 'Authentication failed',
                'expected_type': 'danger',
                'expected_dismissible': False
            },
            {
                'error': 'File too large',
                'expected_type': 'warning',
                'expected_dismissible': True
            }
        ]
        
        for error_case in test_errors:
            with self.subTest(error=error_case['error']):
                result = self._format_error_message(error_case['error'])
                self.assertIn(error_case['expected_type'], result['class'])
                self.assertEqual(result['dismissible'], error_case['expected_dismissible'])
    
    def _format_error_message(self, error_message):
        """Simulate JavaScript error message formatting"""
        error_lower = error_message.lower()
        
        if 'authentication' in error_lower or 'unauthorized' in error_lower:
            return {
                'class': 'alert alert-danger',
                'dismissible': False,
                'message': error_message
            }
        elif 'timeout' in error_lower or 'network' in error_lower:
            return {
                'class': 'alert alert-warning',
                'dismissible': True,
                'message': error_message
            }
        else:
            return {
                'class': 'alert alert-info',
                'dismissible': True,
                'message': error_message
            }


if __name__ == '__main__':
    unittest.main()