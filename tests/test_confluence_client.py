
#!/usr/bin/env python3
"""
Comprehensive unit tests for Confluence API client
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys
import json
from datetime import datetime
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from confluence_client import (
    ConfluenceServerClient, ConfluencePublicationService, ConfluenceConfig,
    ConfluenceContentProcessor, ConfluenceEncryption,
    ConfluenceError, ConfluenceAuthenticationError, ConfluencePermissionError,
    ConfluenceNotFoundError, ConfluenceValidationError, ConfluenceNetworkError,
    create_confluence_client, create_confluence_publication_service
)
from database.models import ConfluencePublication, PublicationStatus


class TestConfluenceConfig(unittest.TestCase):
    """Test cases for ConfluenceConfig dataclass"""
    
    def test_confluence_config_creation(self):
        """Test ConfluenceConfig creation with all parameters"""
        config = ConfluenceConfig(
            base_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='test_token_123',
            space_key='TEST',
            parent_page_id='123456',
            timeout=60,
            max_retries=5,
            retry_delay=2.0
        )
        
        self.assertEqual(config.base_url, 'https://test.atlassian.net/wiki')
        self.assertEqual(config.username, 'test@example.com')
        self.assertEqual(config.api_token, 'test_token_123')
        self.assertEqual(config.space_key, 'TEST')
        self.assertEqual(config.parent_page_id, '123456')
        self.assertEqual(config.timeout, 60)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.retry_delay, 2.0)
    
    def test_confluence_config_defaults(self):
        """Test ConfluenceConfig creation with default values"""
        config = ConfluenceConfig(
            base_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='test_token_123',
            space_key='TEST'
        )
        
        self.assertIsNone(config.parent_page_id)
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.retry_delay, 1.0)


class TestConfluenceEncryption(unittest.TestCase):
    """Test cases for ConfluenceEncryption utilities"""
    
    def test_generate_key(self):
        """Test key generation"""
        key = ConfluenceEncryption.generate_key()
        
        self.assertIsInstance(key, str)
        self.assertGreater(len(key), 0)
        
        # Generate another key and ensure they're different
        key2 = ConfluenceEncryption.generate_key()
        self.assertNotEqual(key, key2)
    
    def test_derive_key_from_password(self):
        """Test key derivation from password"""
        password = "test_password_123"
        key = ConfluenceEncryption.derive_key_from_password(password)
        
        self.assertIsInstance(key, str)
        self.assertGreater(len(key), 0)
        
        # Same password should generate same key
        key2 = ConfluenceEncryption.derive_key_from_password(password)
        self.assertEqual(key, key2)
        
        # Different password should generate different key
        key3 = ConfluenceEncryption.derive_key_from_password("different_password")
        self.assertNotEqual(key, key3)
    
    def test_derive_key_with_custom_salt(self):
        """Test key derivation with custom salt"""
        password = "test_password_123"
        salt = "custom_salt"
        
        key1 = ConfluenceEncryption.derive_key_from_password(password, salt)
        key2 = ConfluenceEncryption.derive_key_from_password(password, salt)
        
        self.assertEqual(key1, key2)
        
        # Different salt should produce different key
        key3 = ConfluenceEncryption.derive_key_from_password(password, "different_salt")
        self.assertNotEqual(key1, key3)
    
    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption"""
        token = "test_api_token_12345"
        key = ConfluenceEncryption.generate_key()
        
        # Encrypt token
        encrypted_token = ConfluenceEncryption.encrypt_token(token, key)
        self.assertIsInstance(encrypted_token, str)
        self.assertNotEqual(encrypted_token, token)
        
        # Decrypt token
        decrypted_token = ConfluenceEncryption.decrypt_token(encrypted_token, key)
        self.assertEqual(decrypted_token, token)
    
    def test_encrypt_decrypt_with_derived_key(self):
        """Test encryption/decryption with password-derived key"""
        token = "test_api_token_12345"
        password = "secure_password_123"
        key = ConfluenceEncryption.derive_key_from_password(password)
        
        encrypted_token = ConfluenceEncryption.encrypt_token(token, key)
        decrypted_token = ConfluenceEncryption.decrypt_token(encrypted_token, key)
        
        self.assertEqual(decrypted_token, token)
    
    def test_decrypt_with_wrong_key(self):
        """Test decryption with wrong key raises error"""
        token = "test_api_token_12345"
        key1 = ConfluenceEncryption.generate_key()
        key2 = ConfluenceEncryption.generate_key()
        
        encrypted_token = ConfluenceEncryption.encrypt_token(token, key1)
        
        with self.assertRaises(ConfluenceError):
            ConfluenceEncryption.decrypt_token(encrypted_token, key2)
    
    def test_encrypt_invalid_key(self):
        """Test encryption with invalid key raises error"""
        token = "test_api_token_12345"
        invalid_key = "invalid_key"
        
        with self.assertRaises(ConfluenceError):
            ConfluenceEncryption.encrypt_token(token, invalid_key)


class TestConfluenceContentProcessor(unittest.TestCase):
    """Test cases for ConfluenceContentProcessor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = ConfluenceContentProcessor()
        self.sample_markdown = """# Meeting Protocol
Date: 2025-09-02
Topic: Confluence Integration Testing

## Participants
- **John Doe** - Developer
- *Jane Smith* - Tester

## Discussion Points
1. Integration with Confluence
2. Testing strategies

### Code Example
```python
def test_function():
    return "Hello, World!"
```

## Decisions
- Implement comprehensive testing
- Use mock data for tests

[Link to documentation](https://example.com/docs)
"""
    
    def test_markdown_to_confluence_headers(self):
        """Test markdown header conversion"""
        markdown = """# Header 1
## Header 2
### Header 3
#### Header 4
##### Header 5
###### Header 6"""
        
        result = self.processor.markdown_to_confluence(markdown)
        
        self.assertIn('<h1>Header 1</h1>', result)
        self.assertIn('<h2>Header 2</h2>', result)
        self.assertIn('<h3>Header 3</h3>', result)
        self.assertIn('<h4>Header 4</h4>', result)
        self.assertIn('<h5>Header 5</h5>', result)
        self.assertIn('<h6>Header 6</h6>', result)
    
    def test_markdown_to_confluence_text_formatting(self):
        """Test markdown text formatting conversion"""
        markdown = """**Bold text** and __also bold__
*Italic text* and _also italic_
`Inline code` example"""
        
        result = self.processor.markdown_to_confluence(markdown)
        
        self.assertIn('<strong>Bold text</strong>', result)
        self.assertIn('<strong>also bold</strong>', result)
        self.assertIn('<em>Italic text</em>', result)
        self.assertIn('<em>also italic</em>', result)
        self.assertIn('<code>Inline code</code>', result)
    
    def test_markdown_to_confluence_code_blocks(self):
        """Test markdown code block conversion"""
        markdown = """```python
def hello_world():
    print("Hello, World!")
    return True
```"""
        
        result = self.processor.markdown_to_confluence(markdown)
        
        self.assertIn('<ac:structured-macro ac:name="code">', result)
        self.assertIn('<ac:parameter ac:name="language">python</ac:parameter>', result)
        self.assertIn('<ac:plain-text-body><![CDATA[', result)
        self.assertIn('def hello_world():', result)
        self.assertIn('print("Hello, World!")', result)
    
    def test_markdown_to_confluence_lists(self):
        """Test markdown list conversion"""
        markdown = """- Item 1
- Item 2
- Item 3

1. Numbered item 1
2. Numbered item 2"""
        
        result = self.processor.markdown_to_confluence(markdown)
        
        self.assertIn('<ul>', result)
        self.assertIn('<li>Item 1</li>', result)
        self.assertIn('<li>Item 2</li>', result)
        self.assertIn('<li>Item 3</li>', result)
        self.assertIn('</ul>', result)
    
    def test_markdown_to_confluence_links(self):
        """Test markdown link conversion"""
        markdown = """[Example Link](https://example.com)
[Documentation](https://docs.example.com)"""
        
        result = self.processor.markdown_to_confluence(markdown)
        
        self.assertIn('<a href="https://example.com">Example Link</a>', result)
        self.assertIn('<a href="https://docs.example.com">Documentation</a>', result)
    
    def test_extract_meeting_info_standard_format(self):
        """Test meeting info extraction from standard format"""
        date, topic = self.processor.extract_meeting_info(self.sample_markdown)
        
        self.assertEqual(date, '2025-09-02')
        self.assertEqual(topic, 'Confluence Integration Testing')
    
    def test_extract_meeting_info_alternative_formats(self):
        """Test meeting info extraction from alternative formats"""
        # Test different date formats
        markdown_formats = [
            "Date: 02.09.2025\nTopic: Test Meeting",
            "Date: 02/09/2025\nTopic: Test Meeting",
            "Date: 2.9.25\nTopic: Test Meeting",
            "Дата: 2025-09-02\nТема: Тестовая встреча"
        ]
        
        for markdown in markdown_formats:
            date, topic = self.processor.extract_meeting_info(markdown)
            self.assertIsNotNone(date)
            self.assertIsNotNone(topic)
    
    def test_extract_meeting_info_from_header(self):
        """Test meeting info extraction from header when explicit fields missing"""
        markdown = """# 2025-09-02 - Weekly Standup Meeting
Some content here"""
        
        date, topic = self.processor.extract_meeting_info(markdown)
        
        self.assertEqual(date, '2025-09-02')
        self.assertEqual(topic, '2025-09-02 - Weekly Standup Meeting')
    
    def test_extract_meeting_info_no_info(self):
        """Test meeting info extraction when no info available"""
        markdown = """# Some Random Content
No date or topic information here"""
        
        date, topic = self.processor.extract_meeting_info(markdown)
        
        # Should extract topic from header even if no explicit date
        self.assertIsNotNone(topic)
        self.assertEqual(topic, 'Some Random Content')
    
    def test_generate_page_title_standard(self):
        """Test page title generation with standard inputs"""
        title = self.processor.generate_page_title(
            meeting_date='2025-09-02',
            meeting_topic='Confluence Integration Testing'
        )
        
        self.assertEqual(title, '20250902 - Confluence Integration Testing')
    
    def test_generate_page_title_different_date_formats(self):
        """Test page title generation with different date formats"""
        test_cases = [
            ('2025-09-02', '20250902'),
            ('02.09.2025', '20250902'),
            ('02/09/2025', '20250902'),
            ('2.9.25', '20250902')
        ]
        
        for input_date, expected_date in test_cases:
            title = self.processor.generate_page_title(
                meeting_date=input_date,
                meeting_topic='Test Meeting'
            )
            self.assertTrue(title.startswith(expected_date))
    
    def test_generate_page_title_no_date(self):
        """Test page title generation without date"""
        title = self.processor.generate_page_title(
            meeting_date=None,
            meeting_topic='Test Meeting'
        )
        
        # Should use current date
        current_date = datetime.now().strftime('%Y%m%d')
        self.assertTrue(title.startswith(current_date))
        self.assertIn('Test Meeting', title)
    
    def test_generate_page_title_no_topic(self):
        """Test page title generation without topic"""
        title = self.processor.generate_page_title(
            meeting_date='2025-09-02',
            meeting_topic=None,
            fallback_filename='meeting_recording.mp3'
        )
        
        self.assertEqual(title, '20250902 - meeting_recording.mp3')
    
    def test_generate_page_title_no_info(self):
        """Test page title generation without any info"""
        title = self.processor.generate_page_title(
            meeting_date=None,
            meeting_topic=None
        )
        
        current_date = datetime.now().strftime('%Y%m%d')
        self.assertEqual(title, f'{current_date} - Протокол встречи')
    
    def test_generate_page_title_special_characters(self):
        """Test page title generation with special characters in topic"""
        title = self.processor.generate_page_title(
            meeting_date='2025-09-02',
            meeting_topic='Meeting with "Special" Characters & Symbols!'
        )
        
        # Should clean special characters
        self.assertNotIn('"', title)
        self.assertNotIn('&', title)
        self.assertNotIn('!', title)
        self.assertIn('Meeting with Special Characters  Symbols', title)


class TestConfluenceServerClient(unittest.TestCase):
    """Test cases for ConfluenceServerClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = ConfluenceConfig(
            base_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='test_token_123',
            space_key='TEST',
            parent_page_id='123456',
            timeout=30,
            max_retries=3,
            retry_delay=1.0
        )
    
    def test_client_initialization(self):
        """Test ConfluenceServerClient initialization"""
        client = ConfluenceServerClient(self.config)
        
        self.assertEqual(client.config, self.config)
        self.assertIsNotNone(client.session)
        self.assertEqual(client.session.auth, (self.config.username, self.config.api_token))
    
    def test_client_validation_missing_base_url(self):
        """Test client validation with missing base_url"""
        invalid_config = ConfluenceConfig(
            base_url='',
            username='test@example.com',
            api_token='test_token_123',
            space_key='TEST'
        )
        
        with self.assertRaises(ConfluenceValidationError):
            ConfluenceServerClient(invalid_config)
    
    def test_client_validation_missing_username(self):
        """Test client validation with missing username"""
        invalid_config = ConfluenceConfig(
            base_url='https://test.atlassian.net/wiki',
            username='',
            api_token='test_token_123',
            space_key='TEST'
        )
        
        with self.assertRaises(ConfluenceValidationError):
            ConfluenceServerClient(invalid_config)
    
    def test_client_validation_missing_api_token(self):
        """Test client validation with missing api_token"""
        invalid_config = ConfluenceConfig(
            base_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='',
            space_key='TEST'
        )
        
        with self.assertRaises(ConfluenceValidationError):
            ConfluenceServerClient(invalid_config)
    
    def test_client_validation_missing_space_key(self):
        """Test client validation with missing space_key"""
        invalid_config = ConfluenceConfig(
            base_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='test_token_123',
            space_key=''
        )
        
        with self.assertRaises(ConfluenceValidationError):
            ConfluenceServerClient(invalid_config)
    
    def test_client_validation_invalid_url(self):
        """Test client validation with invalid URL"""
        invalid_config = ConfluenceConfig(
            base_url='not_a_valid_url',
            username='test@example.com',
            api_token='test_token_123',
            space_key='TEST'
        )
        
        with self.assertRaises(ConfluenceValidationError):
            ConfluenceServerClient(invalid_config)
    
    @patch('confluence_client.requests.Session.request')
    def test_make_request_success(self, mock_request):
        """Test successful HTTP request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        response = client._make_request('GET', '/rest/api/space')
        
        self.assertEqual(response.status_code, 200)
        mock_request.assert_called_once()
    
    @patch('confluence_client.requests.Session.request')
    def test_make_request_authentication_error(self, mock_request):
        """Test HTTP request with authentication error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        
        with self.assertRaises(ConfluenceAuthenticationError):
            client._make_request('GET', '/rest/api/space')
    
    @patch('confluence_client.requests.Session.request')
    def test_make_request_permission_error(self, mock_request):
        """Test HTTP request with permission error"""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        
        with self.assertRaises(ConfluencePermissionError):
            client._make_request('GET', '/rest/api/space')
    
    @patch('confluence_client.requests.Session.request')
    def test_make_request_not_found_error(self, mock_request):
        """Test HTTP request with not found error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        
        with self.assertRaises(ConfluenceNotFoundError):
            client._make_request('GET', '/rest/api/space')
    
    @patch('confluence_client.requests.Session.request')
    def test_make_request_generic_error(self, mock_request):
        """Test HTTP request with generic error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        
        with self.assertRaises(ConfluenceError):
            client._make_request('GET', '/rest/api/space')
    
    @patch('confluence_client.requests.Session.request')
    def test_make_request_network_error(self, mock_request):
        """Test HTTP request with network error"""
        mock_request.side_effect = requests.exceptions.ConnectionError("Network error")
        
        client = ConfluenceServerClient(self.config)
        
        with self.assertRaises(ConfluenceNetworkError):
            client._make_request('GET', '/rest/api/space')
    
    @patch('confluence_client.requests.Session.request')
    def test_make_request_retry_logic(self, mock_request):
        """Test HTTP request retry logic"""
        # First two calls fail, third succeeds
        mock_request.side_effect = [
            requests.exceptions.ConnectionError("Network error"),
            requests.exceptions.ConnectionError("Network error"),
            Mock(status_code=200)
        ]
        
        client = ConfluenceServerClient(self.config)
        response = client._make_request('GET', '/rest/api/space')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 3)
    
    @patch('confluence_client.requests.Session.request')
    def test_test_connection_success(self, mock_request):
        """Test successful connection test"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        result = client.test_connection()
        
        self.assertTrue(result)
    
    @patch('confluence_client.requests.Session.request')
    def test_test_connection_failure(self, mock_request):
        """Test failed connection test"""
        mock_request.side_effect = ConfluenceAuthenticationError("Auth failed")
        
        client = ConfluenceServerClient(self.config)
        result = client.test_connection()
        
        self.assertFalse(result)
    
    @patch('confluence_client.requests.Session.request')
    def test_get_space_info(self, mock_request):
        """Test get space info"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'TEST',
            'name': 'Test Space',
            'type': 'global'
        }
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        space_info = client.get_space_info()
        
        self.assertEqual(space_info['key'], 'TEST')
        self.assertEqual(space_info['name'], 'Test Space')
    
    @patch('confluence_client.requests.Session.request')
    def test_get_page_info(self, mock_request):
        """Test get page info"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '123456',
            'title': 'Test Page',
            'type': 'page',
            'version': {'number': 1}
        }
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        page_info = client.get_page_info('123456')
        
        self.assertEqual(page_info['id'], '123456')
        self.assertEqual(page_info['title'], 'Test Page')
    
    @patch('confluence_client.requests.Session.request')
    def test_create_page(self, mock_request):
        """Test page creation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '789012',
            'title': 'New Test Page',
            'type': 'page',
            '_links': {
                'webui': '/spaces/TEST/pages/789012'
            }
        }
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        page_info = client.create_page(
            title='New Test Page',
            content='<p>Test content</p>'
        )
        
        self.assertEqual(page_info['id'], '789012')
        self.assertEqual(page_info['title'], 'New Test Page')
        
        # Verify the request was made with correct data
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['json']['title'], 'New Test Page')
        self.assertEqual(call_args[1]['json']['body']['storage']['value'], '<p>Test content</p>')
    
    @patch('confluence_client.requests.Session.request')
    def test_update_page(self, mock_request):
        """Test page update"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '789012',
            'title': 'Updated Test Page',
            'type': 'page',
            'version': {'number': 2}
        }
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        page_info = client.update_page(
            page_id='789012',
            title='Updated Test Page',
            content='<p>Updated content</p>',
            version_number=1
        )
        
        self.assertEqual(page_info['id'], '789012')
        self.assertEqual(page_info['title'], 'Updated Test Page')
        self.assertEqual(page_info['version']['number'], 2)
    
    @patch('confluence_client.requests.Session.request')
    def test_delete_page_success(self, mock_request):
        """Test successful page deletion"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        result = client.delete_page('789012')
        
        self.assertTrue(result)
    
    @patch('confluence_client.requests.Session.request')
    def test_delete_page_failure(self, mock_request):
        """Test failed page deletion"""
        mock_request.side_effect = ConfluenceNotFoundError("Page not found")
        
        client = ConfluenceServerClient(self.config)
        result = client.delete_page('789012')
        
        self.assertFalse(result)
    
    @patch('confluence_client.requests.Session.request')
    def test_search_pages(self, mock_request):
        """Test page search"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'id': '123', 'title': 'Search Result 1'},
                {'id': '456', 'title': 'Search Result 2'}
            ]
        }
        mock_request.return_value = mock_response
        
        client = ConfluenceServerClient(self.config)
        results = client.search_pages('test query')
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'Search Result 1')
        self.assertEqual(results[1]['title'], 'Search Result 2')


class TestConfluencePublicationService(unittest.TestCase):
    """Test cases for ConfluencePublicationService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_confluence_client = Mock(spec=ConfluenceServerClient)
        self.mock_db_manager = Mock()
        
        # Configure mock client
        self.mock_confluence_client.config = ConfluenceConfig(
            base_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='test_token_123',
            space_key='TEST'
        )
        
        self.service = ConfluencePublicationService(
            self.mock_confluence_client,
            self.mock_db_manager
        )
    
    def test_service_initialization(self):
        """Test ConfluencePublicationService initialization"""
        self.assertEqual(self.service.confluence_client, self.mock_confluence_client)
        self.assertEqual(self.service.db_manager, self.mock_db_manager)
        self.assertIsInstance(self.service.content_processor, ConfluenceContentProcessor)
    
    def test_publish_meeting_protocol_success(self):
        """Test successful meeting protocol publication"""
        # Mock Confluence API response
        self.mock_confluence_client.create_page.return_value = {
            'id': '789012',
            'title': '20250902 - Test Meeting',
            '_links': {
                'webui': '/spaces/TEST/pages/789012'
            }
        }
        
        # Mock database operations
        self.mock_db_manager.create_confluence_publication.return_value = {
            'id': 1,
            'job_id': 'job_123',
            'confluence_page_id': '789012'
        }
        
        protocol_content = """# Meeting Protocol
Date: 2025-09-02
Topic: Test Meeting

## Participants
- John Doe
- Jane Smith

## Decisions
- Implement testing
"""
        
        publication = self.service.publish_meeting_protocol(
            job_id='job_123',
            protocol_content=protocol_content,
            filename='test_meeting.mp3'
        )
        
        self.assertIsInstance(publication, ConfluencePublication)
        self.assertEqual(publication.job_id, 'job_123')
        self.assertEqual(publication.confluence_page_id, '789012')
        self.assertEqual(publication.publication_status, PublicationStatus.PUBLISHED)
        
        # Verify Confluence API was called
        self.mock_confluence_client.create_page.assert_called_once()
        
        # Verify database was updated
        self.mock_db_manager.create_confluence_publication.assert_called_once()
    
    def test_publish_meeting_protocol_confluence_error(self):
        """Test meeting protocol publication with Confluence error"""
        # Mock Confluence API error
        self.mock_confluence_client.create_page.side_effect = ConfluenceAuthenticationError("Auth failed")
        
        # Mock database operations
        self.mock_db_manager.create_confluence_publication.return_value = {
            'id': 1,
            'job_id': 'job_123',
            'confluence_page_id': ''
        }
        
        protocol_content = """# Meeting Protocol
Date: 2025-09-02
Topic: Test Meeting
"""
        
        with self.assertRaises(ConfluenceError):
            self.service.publish_meeting_protocol(
                job_id='job_123',
                protocol_content=protocol_content
            )
        
        # Verify error publication was saved to database
        self.mock_db_manager.create_confluence_publication.assert_called_once()
        call_args = self.mock_db_manager.create_confluence_publication.call_args[0][0]
        self.assertEqual(call_args['publication_status'], PublicationStatus.FAILED)
        self.assertIn('Auth failed', call_args['error_message'])
    
    def test_retry_failed_publication_success(self):
        """Test successful retry of failed publication"""
        # Mock getting publication from database
        failed_publication = ConfluencePublication(
            id=1,
            job_id='job_123',
            confluence_page_id='',
            confluence_page_url='',
            confluence_space_key='TEST',
            page_title='Failed Publication',
            publication_status=PublicationStatus.FAILED,
            error_message='Previous error'
        )
        
        self.mock_db_manager.get_confluence_publication_by_id.return_value = failed_publication.to_dict()
        
        # Mock getting job from database
        self.mock_db_manager.get_job_by_id.return_value = {
            'job_id': 'job_123',
            'summary_file': '/path/to/summary.md',
            'filename': 'test_meeting.mp3'
        }
        
        # Mock file reading
        with patch('builtins.open', unittest.mock.mock_open(read_data='# Test Protocol')):
            # Mock successful Confluence API call
            self.mock_confluence_client.create_page.return_value = {
                'id': '789012',
                'title': '20250902 - Test Meeting',
                '_links': {'webui': '/spaces/TEST/pages/789012'}
            }
            
            # Mock database operations
            self.mock_db_manager.create_confluence_publication.return_value = {
                'id': 2,
                'job_id': 'job_123',
                'confluence_page_id': '789012'
            }
            
            publication = self.service.retry_failed_publication(1)
            
            self.assertIsInstance(publication, ConfluencePublication)
            self.assertEqual(publication.publication_status, PublicationStatus.PUBLISHED)
    
    def test_retry_failed_publication_not_found(self):
        """Test retry of non-existent publication"""
        self.mock_db_manager.get_confluence_publication_by_id.return_value = None
        
        with self.assertRaises(ConfluenceNotFoundError):
            self.service.retry_failed_publication(999)
    
    def test_retry_failed_publication_not_failed(self):
        """Test retry of publication that is not failed"""
        published_publication = ConfluencePublication(
            id=1,
            job_id='job_123',
            confluence_page_id='789012',
            confluence_page_url='https://test.atlassian.net/wiki/spaces/TEST/pages/789012',
            confluence_space_key='TEST',
            page_title='Published Page',
            publication_status=PublicationStatus.PUBLISHED
        )
        
        self.mock_db_manager.get_confluence_publication_by_id.return_value = published_publication.to_dict()
        
        with self.assertRaises(ConfluenceValidationError):
            self.service.retry_failed_publication(1)
    
    def test_get_job_publications(self):
        """Test getting publications for a job"""
        mock_publications = [
            {
                'id': 1,
                'job_id': 'job_123',
                'confluence_page_id': '789012',
                'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/789012',
                'confluence_space_key': 'TEST',
                'page_title': 'Test Publication',
                'publication_status': PublicationStatus.PUBLISHED,
                'created_at': '2025-09-02T12:00:00Z',
                'updated_at': '2025-09-02T12:00:00Z',
                'error_message': None,
                'retry_count': 0,
                'last_retry_at': None
            }
        ]
        
        self.mock_db_manager.get_confluence_publications_by_job_id.return_value = mock_publications
        
        publications = self.service.get_job_publications('job_123')
        
        self.assertEqual(len(publications), 1)
        self.assertIsInstance(publications[0], ConfluencePublication)
        self.assertEqual(publications[0].job_id, 'job_123')
    
    def test_delete_publication_success(self):
        """Test successful publication deletion"""
        publication = ConfluencePublication(
            id=1,
            job_id='job_123',
            confluence_page_id='789012',
            confluence_page_url='https://test.atlassian.net/wiki/spaces/TEST/pages/789012',
            confluence_space_key='TEST',
            page_title='Test Publication',
            publication_status=PublicationStatus.PUBLISHED
        )
        
        self.mock_db_manager.get_confluence_publication_by_id.return_value = publication.to_dict()
        self.mock_confluence_client.delete_page.return_value = True
        self.mock_db_manager.delete_confluence_publication.return_value = True
        
        result = self.service.delete_publication(1, delete_from_confluence=True)
        
        self.assertTrue(result)
        self.mock_confluence_client.delete_page.assert_called_once_with('789012')
        self.mock_db_manager.delete_confluence_publication.assert_called_once_with(1)
    
    def test_delete_publication_not_found(self):
        """Test deletion of non-existent publication"""
        self.mock_db_manager.get_confluence_publication_by_id.return_value = None
        
        result = self.service.delete_publication(999)
        
        self.assertFalse(result)


class TestConfluenceFactoryFunctions(unittest.TestCase):
    """Test cases for Confluence factory functions"""
    
    def test_create_confluence_client_success(self):
        """Test successful Confluence client creation"""
        config = {
            'confluence': {
                'enabled': True,
                'base_url': 'https://test.atlassian.net/wiki',
                'username': 'test@example.com',
                'api_token': 'test_token_123',
                'space_key': 'TEST',
                'timeout': 60,
                'max_retries': 5
            }
        }
        
        client = create_confluence_client(config)
        
        self.assertIsInstance(client, ConfluenceServerClient)
        self.assertEqual(client.config.base_url, 'https://test.atlassian.net/wiki')
        self.assertEqual(client.config.username, 'test@example.com')
        self.assertEqual(client.config.space_key, 'TEST')
        self.assertEqual(client.config.timeout, 60)
        self.assertEqual(client.config.max_retries, 5)
    
    def test_create_confluence_client_disabled(self):
        """Test Confluence client creation when disabled"""
        config = {
            'confluence': {
                'enabled': False,
                'base_url': 'https://test.atlassian.net/wiki',
                'username': 'test@example.com',
                'api_token': 'test_token_123',
                'space_key': 'TEST'
            }
        }
        
        with self.assertRaises(ConfluenceValidationError):
            create_confluence_client(config)
    
    def test_create_confluence_client_with_encryption(self):
        """Test Confluence client creation with encrypted token"""
        # Create encrypted token
        original_token = 'test_token_123'
        encryption_key = ConfluenceEncryption.generate_key()
        encrypted_token = ConfluenceEncryption.encrypt_token(original_token, encryption_key)
        
        config = {
            'confluence': {
                'enabled': True,
                'base_url': 'https://test.atlassian.net/wiki',
                'username': 'test@example.com',
                'api_token': encrypted_token,
                'encryption_key': encryption_key,
                'space_key': 'TEST'
            }
        }
        
        client = create_confluence_client(config)
        
        self.assertIsInstance(client, ConfluenceServerClient)
        self.assertEqual(client.config.api_token, original_token)
    
    def test_create_confluence_publication_service(self):
        """Test Confluence publication service creation"""
        config = {
            'confluence': {
                'enabled': True,
                'base_url': 'https://test.atlassian.net/wiki',
                'username': 'test@example.com',
                'api_token': 'test_token_123',
                'space_key': 'TEST'
            }
        }
        
        mock_db_manager = Mock()
        
        service = create_confluence_publication_service(config, mock_db_manager)
        
        self.assertIsInstance(service, ConfluencePublicationService)
        self.assertIsInstance(service.confluence_client, ConfluenceServerClient)
        self.assertEqual(service.db_manager, mock_db_manager)


if __name__ == '__main__':
    unittest.main()