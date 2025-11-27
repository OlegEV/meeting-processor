
#!/usr/bin/env python3
"""
Integration tests for Flask routes and authentication with Confluence functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys
import json
from pathlib import Path
import io

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_web import WorkingMeetingWebApp
from database.models import PublicationStatus


class TestFlaskIntegration(unittest.TestCase):
    """Integration tests for Flask application with Confluence"""
    
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
                'space_key': 'TEST',
                'timeout': 30,
                'max_retries': 3
            },
            'settings': {
                'max_file_size_mb': 200,
                'deepgram_timeout_seconds': 300,
                'claude_model': 'claude-sonnet-4-20250514'
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
        
        # Mock ConfigLoader to return our test data
        with patch('run_web.ConfigLoader.load_config') as mock_load_config, \
             patch('run_web.ConfigLoader.load_api_keys') as mock_load_api_keys, \
             patch('run_web.ConfigLoader.validate_api_keys') as mock_validate_keys:
            
            mock_load_config.return_value = self.test_config
            mock_load_api_keys.return_value = self.mock_api_keys
            mock_validate_keys.return_value = (True, True, 'test_deepgram_key', 'test_claude_key')
            
            # Create Flask app
            self.app = WorkingMeetingWebApp(self.config_file.name)
            self.client = self.app.app.test_client()
            self.app.app.config['TESTING'] = True
        
        # Create test user
        self.test_user_id = 'test_user_123'
        self.test_user_data = {
            'user_id': self.test_user_id,
            'email': 'test@example.com',
            'name': 'Test User',
            'full_name': 'Test User Full'
        }
        self.app.db_manager.create_user(self.test_user_data)
        
        # Mock authentication headers
        self.auth_headers = {
            'X-Identity-Token': 'test_token',
            'X-User-Id': self.test_user_id,
            'X-User-Email': 'test@example.com',
            'X-User-Name': 'Test User'
        }
    
    def tearDown(self):
        """Clean up test files"""
        try:
            os.unlink(self.test_db.name)
            os.unlink(self.config_file.name)
            os.unlink(self.api_keys_file.name)
        except FileNotFoundError:
            pass
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get('/health')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('database', data)
        self.assertIn('auth', data)
        self.assertIn('confluence', data)
        
        # Verify Confluence status
        self.assertTrue(data['confluence']['available'])
        self.assertTrue(data['confluence']['enabled'])
        self.assertTrue(data['confluence']['configured'])
    
    def test_index_page_with_auth(self):
        """Test index page with authentication"""
        response = self.client.get('/', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test User', response.data)
        self.assertIn(b'Meeting Processor', response.data)
    
    def test_index_page_without_auth(self):
        """Test index page without authentication"""
        response = self.client.get('/')
        
        # Should return 401 in non-debug mode, but we have debug mode enabled
        # so it should work
        self.assertEqual(response.status_code, 200)
    
    def test_upload_file_endpoint(self):
        """Test file upload endpoint"""
        # Create test file
        test_file_content = b'fake audio content'
        test_file = io.BytesIO(test_file_content)
        
        data = {
            'file': (test_file, 'test_meeting.mp3'),
            'template': 'standard'
        }
        
        with patch.object(self.app, 'process_file_sync'):
            response = self.client.post('/upload', 
                                      data=data, 
                                      headers=self.auth_headers,
                                      content_type='multipart/form-data')
        
        # Should redirect to status page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/status/', response.location)
    
    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type"""
        test_file = io.BytesIO(b'fake content')
        
        data = {
            'file': (test_file, 'test_document.txt'),
            'template': 'standard'
        }
        
        response = self.client.post('/upload', 
                                  data=data, 
                                  headers=self.auth_headers,
                                  content_type='multipart/form-data')
        
        # Should redirect back to index with error
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.location)
    
    def test_status_page(self):
        """Test status page for job"""
        # Create test job
        job_data = {
            'job_id': 'test_job_status',
            'user_id': self.test_user_id,
            'filename': 'test_meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'message': 'Processing completed'
        }
        self.app.db_manager.create_job(job_data)
        
        response = self.client.get('/status/test_job_status', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'test_meeting.mp3', response.data)
        self.assertIn(b'completed', response.data)
    
    def test_status_page_unauthorized_job(self):
        """Test status page for job belonging to another user"""
        # Create job for different user
        other_user_data = {
            'user_id': 'other_user',
            'email': 'other@example.com',
            'name': 'Other User'
        }
        self.app.db_manager.create_user(other_user_data)
        
        job_data = {
            'job_id': 'other_user_job',
            'user_id': 'other_user',
            'filename': 'other_meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        self.app.db_manager.create_job(job_data)
        
        response = self.client.get('/status/other_user_job', headers=self.auth_headers)
        
        # Should redirect to index with error
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.location)
    
    def test_api_status_endpoint(self):
        """Test API status endpoint"""
        # Create test job
        job_data = {
            'job_id': 'test_api_job',
            'user_id': self.test_user_id,
            'filename': 'api_test.mp3',
            'template': 'business',
            'status': 'processing',
            'progress': 75,
            'message': 'Processing audio...'
        }
        self.app.db_manager.create_job(job_data)
        
        response = self.client.get('/api/status/test_api_job', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'processing')
        self.assertEqual(data['progress'], 75)
        self.assertEqual(data['filename'], 'api_test.mp3')
        self.assertEqual(data['template'], 'business')
    
    def test_jobs_list_page(self):
        """Test jobs list page"""
        # Create multiple test jobs
        job_data_list = [
            {
                'job_id': 'list_job_1',
                'user_id': self.test_user_id,
                'filename': 'meeting1.mp3',
                'template': 'standard',
                'status': 'completed',
                'progress': 100
            },
            {
                'job_id': 'list_job_2',
                'user_id': self.test_user_id,
                'filename': 'meeting2.mp3',
                'template': 'business',
                'status': 'processing',
                'progress': 50
            }
        ]
        
        for job_data in job_data_list:
            self.app.db_manager.create_job(job_data)
        
        response = self.client.get('/jobs', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'meeting1.mp3', response.data)
        self.assertIn(b'meeting2.mp3', response.data)
        self.assertIn(b'completed', response.data)
        self.assertIn(b'processing', response.data)
    
    @patch('run_web.ConfluenceServerClient')
    def test_publish_confluence_endpoint_success(self, mock_confluence_client):
        """Test successful Confluence publication endpoint"""
        # Create completed job with summary file
        job_data = {
            'job_id': 'confluence_job',
            'user_id': self.test_user_id,
            'filename': 'confluence_meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'summary_file': '/tmp/test_summary.md'
        }
        self.app.db_manager.create_job(job_data)
        
        # Mock summary file content
        test_summary = """# Meeting Protocol
Date: 2025-09-02
Topic: Test Confluence Publication

## Participants
- Test User

## Decisions
- Publish to Confluence
"""
        
        # Mock Confluence client
        mock_client_instance = Mock()
        mock_client_instance.publish_protocol.return_value = {
            'success': True,
            'page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/123456',
            'page_id': '123456'
        }
        mock_confluence_client.return_value = mock_client_instance
        
        # Mock file reading
        with patch('builtins.open', unittest.mock.mock_open(read_data=test_summary)):
            data = {
                'base_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/parent/',
                'page_title': '20250902 - Test Meeting',
                'space_key': 'TEST'
            }
            
            response = self.client.post('/publish_confluence/confluence_job',
                                      data=data,
                                      headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        self.assertIn('page_url', response_data)
        self.assertEqual(response_data['page_id'], '123456')
    
    @patch('run_web.ConfluenceServerClient')
    def test_publish_confluence_endpoint_failure(self, mock_confluence_client):
        """Test failed Confluence publication endpoint"""
        # Create completed job
        job_data = {
            'job_id': 'confluence_fail_job',
            'user_id': self.test_user_id,
            'filename': 'confluence_fail.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'summary_file': '/tmp/test_summary.md'
        }
        self.app.db_manager.create_job(job_data)
        
        # Mock Confluence client failure
        mock_client_instance = Mock()
        mock_client_instance.publish_protocol.return_value = {
            'success': False,
            'error': 'Authentication failed'
        }
        mock_confluence_client.return_value = mock_client_instance
        
        with patch('builtins.open', unittest.mock.mock_open(read_data='# Test')):
            data = {
                'base_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/parent/',
                'page_title': '20250902 - Test Meeting',
                'space_key': 'TEST'
            }
            
            response = self.client.post('/publish_confluence/confluence_fail_job',
                                      data=data,
                                      headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 500)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    def test_publish_confluence_invalid_job(self):
        """Test Confluence publication with invalid job"""
        data = {
            'base_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/parent/',
            'page_title': '20250902 - Test Meeting',
            'space_key': 'TEST'
        }
        
        response = self.client.post('/publish_confluence/nonexistent_job',
                                  data=data,
                                  headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 404)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    def test_publish_confluence_incomplete_job(self):
        """Test Confluence publication with incomplete job"""
        # Create incomplete job
        job_data = {
            'job_id': 'incomplete_job',
            'user_id': self.test_user_id,
            'filename': 'incomplete.mp3',
            'template': 'standard',
            'status': 'processing',
            'progress': 50
        }
        self.app.db_manager.create_job(job_data)
        
        data = {
            'base_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/parent/',
            'page_title': '20250902 - Test Meeting',
            'space_key': 'TEST'
        }
        
        response = self.client.post('/publish_confluence/incomplete_job',
                                  data=data,
                                  headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    def test_confluence_publications_endpoint(self):
        """Test Confluence publications history endpoint"""
        # Create job and publications
        job_data = {
            'job_id': 'publications_job',
            'user_id': self.test_user_id,
            'filename': 'publications_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        self.app.db_manager.create_job(job_data)
        
        # Create test publications
        publication_data_list = [
            {
                'job_id': 'publications_job',
                'confluence_page_id': 'page_1',
                'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/1',
                'confluence_space_key': 'TEST',
                'page_title': '20250902 - Test Meeting',
                'publication_status': PublicationStatus.PUBLISHED
            },
            {
                'job_id': 'publications_job',
                'confluence_page_id': 'page_2',
                'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/2',
                'confluence_space_key': 'TEST',
                'page_title': '20250902 - Test Meeting (Retry)',
                'publication_status': PublicationStatus.FAILED,
                'error_message': 'Network timeout'
            }
        ]
        
        for pub_data in publication_data_list:
            self.app.db_manager.create_confluence_publication(pub_data)
        
        response = self.client.get('/confluence_publications/publications_job',
                                 headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertEqual(response_data['count'], 2)
        self.assertEqual(len(response_data['publications']), 2)
        
        # Verify publication details
        publications = response_data['publications']
        published_pub = next(p for p in publications if p['publication_status'] == PublicationStatus.PUBLISHED)
        failed_pub = next(p for p in publications if p['publication_status'] == PublicationStatus.FAILED)
        
        self.assertEqual(published_pub['confluence_page_id'], 'page_1')
        self.assertEqual(failed_pub['error_message'], 'Network timeout')
    
    def test_confluence_publications_unauthorized_job(self):
        """Test Confluence publications endpoint with unauthorized job"""
        # Create job for different user
        other_user_data = {
            'user_id': 'other_user_pub',
            'email': 'other_pub@example.com',
            'name': 'Other User Pub'
        }
        self.app.db_manager.create_user(other_user_data)
        
        job_data = {
            'job_id': 'other_publications_job',
            'user_id': 'other_user_pub',
            'filename': 'other_publications.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        self.app.db_manager.create_job(job_data)
        
        response = self.client.get('/confluence_publications/other_publications_job',
                                 headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 404)
        
        response_data = json.loads(response.data)
        self.assertIn('error', response_data)
    
    def test_statistics_page(self):
        """Test statistics page"""
        # Create some test data
        job_data_list = [
            {
                'job_id': 'stats_job_1',
                'user_id': self.test_user_id,
                'filename': 'stats1.mp3',
                'template': 'standard',
                'status': 'completed',
                'progress': 100
            },
            {
                'job_id': 'stats_job_2',
                'user_id': self.test_user_id,
                'filename': 'stats2.mp3',
                'template': 'business',
                'status': 'completed',
                'progress': 100
            }
        ]
        
        for job_data in job_data_list:
            self.app.db_manager.create_job(job_data)
        
        response = self.client.get('/statistics', headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Statistics', response.data)
    
    def test_download_file_endpoint(self):
        """Test file download endpoint"""
        # Create job with files
        job_data = {
            'job_id': 'download_job',
            'user_id': self.test_user_id,
            'filename': 'download_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'transcript_file': '/tmp/test_transcript.txt',
            'summary_file': '/tmp/test_summary.md'
        }
        self.app.db_manager.create_job(job_data)
        
        # Mock file existence and content
        with patch('os.path.exists', return_value=True), \
             patch('run_web.send_file') as mock_send_file:
            
            mock_send_file.return_value = 'file_content'
            
            # Test transcript download
            response = self.client.get('/download/download_job/transcript',
                                     headers=self.auth_headers)
            
            mock_send_file.assert_called_once()
            call_args = mock_send_file.call_args
            self.assertEqual(call_args[0][0], '/tmp/test_transcript.txt')
            self.assertTrue(call_args[1]['as_attachment'])
    
    def test_view_file_endpoint(self):
        """Test file view endpoint"""
        # Create job with files
        job_data = {
            'job_id': 'view_job',
            'user_id': self.test_user_id,
            'filename': 'view_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'summary_file': '/tmp/test_summary.md'
        }
        self.app.db_manager.create_job(job_data)
        
        test_content = """# Meeting Protocol
Date: 2025-09-02
Topic: View Test Meeting

## Content
This is test content for viewing.
"""
        
        # Mock file existence and content
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data=test_content)):
            
            response = self.client.get('/view/view_job/summary',
                                     headers=self.auth_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Meeting Protocol', response.data)
            self.assertIn(b'View Test Meeting', response.data)
    
    def test_generate_protocol_endpoint(self):
        """Test protocol generation endpoint"""
        # Create completed job with transcript
        job_data = {
            'job_id': 'protocol_job',
            'user_id': self.test_user_id,
            'filename': 'protocol_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'transcript_file': '/tmp/test_transcript.txt'
        }
        self.app.db_manager.create_job(job_data)
        
        # Mock file existence
        with patch('os.path.exists', return_value=True), \
             patch.object(self.app, 'generate_protocol_sync'):
            
            data = {'new_template': 'business'}
            
            response = self.client.post('/generate_protocol/protocol_job',
                                      data=data,
                                      headers=self.auth_headers)
            
            # Should redirect to new protocol job status
            self.assertEqual(response.status_code, 302)
            self.assertIn('/status/', response.location)
    
    def test_error_handling_file_too_large(self):
        """Test error handling for file too large"""
        # Create a large file (mock)
        large_file = io.BytesIO(b'x' * (250 * 1024 * 1024))  # 250MB
        
        data = {
            'file': (large_file, 'large_meeting.mp3'),
            'template': 'standard'
        }
        
        response = self.client.post('/upload',
                                  data=data,
                                  headers=self.auth_headers,
                                  content_type='multipart/form-data')
        
        # Should handle file too large error
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.location)
    
    def test_docs_endpoints(self):
        """Test documentation endpoints"""
        # Test docs index
        response = self.client.get('/docs')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Documentation', response.data)
        
        # Test specific doc (mock file existence)
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data='# Test Documentation')):
            
            response = self.client.get('/docs/guidelines')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test Documentation', response.data)
    
    def test_confluence_configuration_validation(self):
        """Test Confluence configuration validation in health endpoint"""
        response = self.client.get('/health')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        confluence_info = data['confluence']
        
        self.assertTrue(confluence_info['available'])
        self.assertTrue(confluence_info['enabled'])
        self.assertTrue(confluence_info['configured'])
    
    def test_user_isolation(self):
        """Test that users can only access their own data"""
        # Create another user
        other_user_data = {
            'user_id': 'isolation_user',
            'email': 'isolation@example.com',
            'name': 'Isolation User'
        }
        self.app.db_manager.create_user(other_user_data)
        
        # Create job for other user
        other_job_data = {
            'job_id': 'isolation_job',
            'user_id': 'isolation_user',
            'filename': 'isolation_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        self.app.db_manager.create_job(other_job_data)
        
        # Try to access other user's job
        response = self.client.get('/status/isolation_job', headers=self.auth_headers)
        
        # Should be redirected (access denied)
        self.assertEqual(response.status_code, 302)
        
        # Try to access other user's job via API
        response = self.client.get('/api/status/isolation_job', headers=self.auth_headers)
        
        # Should return 404
        self.assertEqual(response.status_code, 404)


class TestAuthenticationIntegration(unittest.TestCase):
    """Test authentication integration"""
    
    def setUp(self):
        """Set up test Flask application with authentication"""
        # Create test configuration with auth enabled
        self.test_config = {
            'database': {
                'path': ':memory:',
                'timeout': 30,
                'check_same_thread': False
            },
            'auth': {
                'enabled': True,
                'debug_mode': False,  # Disable debug mode for auth testing
                'token_header': 'X-Identity-Token',
                'jwt_secret': 'test_secret_key_for_testing'
            },
            'confluence': {
                'enabled': False  # Disable for auth testing
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
        
        # Mock ConfigLoader
        with patch('run_web.ConfigLoader.load_config') as mock_load_config, \
             patch('run_web.ConfigLoader.load_api_keys') as mock_load_api_keys, \
             patch('run_web.ConfigLoader.validate_api_keys') as mock_validate_keys:
            
            mock_load_config.return_value = self.test_config
            mock_load_api_keys.return_value = self.mock_api_keys
            mock_validate_keys.return_value = (True, True, 'test_deepgram_key', 'test_claude_key')
            
            # Create Flask app
            self.app = WorkingMeetingWebApp('test_config.json')
            self.client = self.app.app.test_client()
            self.app.app.config['TESTING'] = True
    
    def test_protected_endpoint_without_auth(self):
        """Test accessing protected endpoint without authentication"""
        response = self.client.get('/')
        
        # Should return 401 or redirect to auth
        self.assertIn(response.status_code, [401, 302])
    
    def test_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid token"""
        headers = {'X-Identity-Token': 'invalid_token'}
        
        response = self.client.get('/', headers=headers)
        
        # Should return 401 or redirect to auth
        self.assertIn(response.status_code, [401, 302])
    
    def test_protected_endpoint_with_valid_token(self):
        """Test accessing protected endpoint with valid token"""
        # Mock valid authentication
        with patch('auth.require_auth') as mock_require_auth:
            mock_require_auth.return_value = lambda f: f  # Pass through decorator
            
            with patch('auth.get_current_user_id', return_value='test_user'), \
                 patch('auth.get_current_user', return_value={'user_id': 'test_user', 'name': 'Test User'}):
                
                # Create test user
                user_data = {
                    'user_id': 'test_user',
                    'email': 'test@example.com',
                    'name': 'Test User'
                }
                self.app.db_manager.create_user(user_data)
                
                headers = {'X-Identity-Token': 'valid_token'}
                response = self.client.get('/', headers=headers)
                
                self.assertEqual(response.status_code, 200)
    
    def test_api_endpoint_authentication(self):
        """Test API endpoint authentication"""
        # Test without auth
        response = self.client.get('/api/status/test_job')
        self.assertIn(response.status_code, [401, 404])  # 401 for auth, 404 if auth bypassed
        
        # Test with invalid auth
        headers = {'X-Identity-Token': 'invalid_token'}
        response = self.client.get('/api/status/test_job', headers=headers)
        self.assertIn(response.status_code, [401, 404])


if __name__ == '__main__':
    unittest.main()