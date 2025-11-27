
#!/usr/bin/env python3
"""
End-to-end workflow tests for the complete Confluence publication workflow
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import os
import sys
import json
import time
import threading
from pathlib import Path
import io

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_web import WorkingMeetingWebApp
from database.models import PublicationStatus
from confluence_client import ConfluenceServerClient, ConfluencePublicationService


class TestCompleteWorkflow(unittest.TestCase):
    """End-to-end tests for complete Confluence publication workflow"""
    
    def setUp(self):
        """Set up complete test environment"""
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
                'max_retries': 3,
                'retry_delay': 1.0
            },
            'settings': {
                'max_file_size_mb': 200,
                'deepgram_timeout_seconds': 300,
                'claude_model': 'claude-sonnet-4-20250514',
                'chunk_duration_minutes': 15
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
            self.client = self.app.app.test_client()
            self.app.app.config['TESTING'] = True
        
        # Create test user
        self.test_user_id = 'e2e_test_user'
        self.test_user_data = {
            'user_id': self.test_user_id,
            'email': 'e2e@example.com',
            'name': 'E2E Test User',
            'full_name': 'End-to-End Test User'
        }
        self.app.db_manager.create_user(self.test_user_data)
        
        # Mock authentication headers
        self.auth_headers = {
            'X-Identity-Token': 'e2e_test_token',
            'X-User-Id': self.test_user_id,
            'X-User-Email': 'e2e@example.com',
            'X-User-Name': 'E2E Test User'
        }
        
        # Test protocol content
        self.test_protocol_content = """# Meeting Protocol
Date: 2025-09-02
Topic: End-to-End Testing of Confluence Integration

## Participants
- **E2E Test User** - Test Engineer
- **System** - Automated Testing System

## Discussion Points
1. Complete workflow testing
2. Confluence integration validation
3. Error handling verification

### Technical Details
```python
def test_confluence_integration():
    return "Testing complete workflow"
```

## Decisions Made
- Implement comprehensive end-to-end testing
- Validate all integration points
- Ensure error handling works correctly

## Action Items
- [ ] Complete workflow testing
- [ ] Validate Confluence publication
- [ ] Test error scenarios

## Next Steps
Continue with performance testing and documentation.
"""
    
    def tearDown(self):
        """Clean up test files"""
        try:
            os.unlink(self.test_db.name)
            os.unlink(self.config_file.name)
            os.unlink(self.api_keys_file.name)
        except FileNotFoundError:
            pass
    
    def test_complete_meeting_processing_workflow(self):
        """Test complete workflow from file upload to protocol generation"""
        # Step 1: Upload file
        test_file_content = b'fake audio content for testing'
        test_file = io.BytesIO(test_file_content)
        
        data = {
            'file': (test_file, 'e2e_test_meeting.mp3'),
            'template': 'standard'
        }
        
        # Mock the file processing to avoid actual audio processing
        with patch.object(self.app, 'process_file_sync') as mock_process:
            response = self.client.post('/upload', 
                                      data=data, 
                                      headers=self.auth_headers,
                                      content_type='multipart/form-data')
            
            # Should redirect to status page
            self.assertEqual(response.status_code, 302)
            self.assertIn('/status/', response.location)
            
            # Extract job_id from redirect URL
            job_id = response.location.split('/status/')[-1]
            
            # Verify job was created in database
            job = self.app.db_manager.get_job_by_id(job_id, self.test_user_id)
            self.assertIsNotNone(job)
            self.assertEqual(job['filename'], 'e2e_test_meeting.mp3')
            self.assertEqual(job['template'], 'standard')
            self.assertEqual(job['status'], 'uploaded')
            
            # Verify process_file_sync was called
            mock_process.assert_called_once_with(job_id)
        
        # Step 2: Simulate processing completion
        # Create temporary output files
        temp_dir = tempfile.mkdtemp()
        transcript_file = os.path.join(temp_dir, 'e2e_test_meeting_transcript.txt')
        summary_file = os.path.join(temp_dir, 'e2e_test_meeting_summary.md')
        
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write("This is a test transcript of the meeting.")
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self.test_protocol_content)
        
        # Update job status to completed
        update_data = {
            'status': 'completed',
            'progress': 100,
            'message': 'Processing completed successfully',
            'transcript_file': transcript_file,
            'summary_file': summary_file
        }
        self.app.db_manager.update_job(job_id, update_data, self.test_user_id)
        
        # Step 3: Verify status page shows completion
        response = self.client.get(f'/status/{job_id}', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'completed', response.data)
        self.assertIn(b'e2e_test_meeting.mp3', response.data)
        
        # Step 4: Test file download
        response = self.client.get(f'/download/{job_id}/transcript', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(f'/download/{job_id}/summary', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        
        # Step 5: Test file viewing
        response = self.client.get(f'/view/{job_id}/summary', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'End-to-End Testing', response.data)
        
        # Cleanup
        try:
            os.unlink(transcript_file)
            os.unlink(summary_file)
            os.rmdir(temp_dir)
        except:
            pass
    
    @patch('confluence_client.ConfluenceServerClient')
    def test_complete_confluence_publication_workflow(self, mock_confluence_client):
        """Test complete Confluence publication workflow"""
        # Step 1: Create completed job with protocol
        job_id = 'e2e_confluence_job'
        
        # Create temporary protocol file
        temp_dir = tempfile.mkdtemp()
        summary_file = os.path.join(temp_dir, 'confluence_test_summary.md')
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self.test_protocol_content)
        
        job_data = {
            'job_id': job_id,
            'user_id': self.test_user_id,
            'filename': 'confluence_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'message': 'Processing completed',
            'summary_file': summary_file
        }
        self.app.db_manager.create_job(job_data)
        
        # Step 2: Mock Confluence client for successful publication
        mock_client_instance = Mock()
        mock_client_instance.create_page.return_value = {
            'id': '123456',
            'title': '20250902 - End-to-End Testing of Confluence Integration',
            '_links': {
                'webui': '/spaces/TEST/pages/123456'
            }
        }
        mock_confluence_client.return_value = mock_client_instance
        
        # Step 3: Publish to Confluence
        publication_data = {
            'base_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/parent/',
            'page_title': '20250902 - E2E Test Meeting',
            'space_key': 'TEST'
        }
        
        response = self.client.post(f'/publish_confluence/{job_id}',
                                  data=publication_data,
                                  headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        self.assertIn('page_url', response_data)
        
        # Step 4: Verify publication was saved to database
        publications = self.app.db_manager.get_confluence_publications_by_job_id(job_id)
        self.assertEqual(len(publications), 1)
        
        publication = publications[0]
        self.assertEqual(publication['confluence_page_id'], '123456')
        self.assertEqual(publication['publication_status'], PublicationStatus.PUBLISHED)
        self.assertEqual(publication['confluence_space_key'], 'TEST')
        
        # Step 5: Test publication history retrieval
        response = self.client.get(f'/confluence_publications/{job_id}', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        
        history_data = json.loads(response.data)
        self.assertEqual(history_data['count'], 1)
        self.assertEqual(len(history_data['publications']), 1)
        
        # Cleanup
        try:
            os.unlink(summary_file)
            os.rmdir(temp_dir)
        except:
            pass
    
    @patch('confluence_client.ConfluenceServerClient')
    def test_confluence_publication_failure_and_retry_workflow(self, mock_confluence_client):
        """Test Confluence publication failure and retry workflow"""
        # Step 1: Create completed job
        job_id = 'e2e_retry_job'
        
        temp_dir = tempfile.mkdtemp()
        summary_file = os.path.join(temp_dir, 'retry_test_summary.md')
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self.test_protocol_content)
        
        job_data = {
            'job_id': job_id,
            'user_id': self.test_user_id,
            'filename': 'retry_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'summary_file': summary_file
        }
        self.app.db_manager.create_job(job_data)
        
        # Step 2: Mock Confluence client for failure
        mock_client_instance = Mock()
        mock_client_instance.create_page.side_effect = Exception("Network timeout")
        mock_confluence_client.return_value = mock_client_instance
        
        # Step 3: Attempt publication (should fail)
        publication_data = {
            'base_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/parent/',
            'page_title': '20250902 - Retry Test Meeting',
            'space_key': 'TEST'
        }
        
        response = self.client.post(f'/publish_confluence/{job_id}',
                                  data=publication_data,
                                  headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 500)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
        
        # Step 4: Verify failed publication was saved
        publications = self.app.db_manager.get_confluence_publications_by_job_id(job_id)
        self.assertEqual(len(publications), 1)
        
        failed_publication = publications[0]
        self.assertEqual(failed_publication['publication_status'], PublicationStatus.FAILED)
        self.assertIn('Network timeout', failed_publication['error_message'])
        
        # Step 5: Mock successful retry
        mock_client_instance.create_page.side_effect = None
        mock_client_instance.create_page.return_value = {
            'id': '789012',
            'title': '20250902 - Retry Test Meeting',
            '_links': {
                'webui': '/spaces/TEST/pages/789012'
            }
        }
        
        # Step 6: Retry publication
        response = self.client.post(f'/publish_confluence/{job_id}',
                                  data=publication_data,
                                  headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        
        # Step 7: Verify successful publication was saved
        publications = self.app.db_manager.get_confluence_publications_by_job_id(job_id)
        self.assertEqual(len(publications), 2)  # Failed + successful
        
        successful_publication = next(p for p in publications if p['publication_status'] == PublicationStatus.PUBLISHED)
        self.assertEqual(successful_publication['confluence_page_id'], '789012')
        
        # Cleanup
        try:
            os.unlink(summary_file)
            os.rmdir(temp_dir)
        except:
            pass
    
    def test_protocol_regeneration_workflow(self):
        """Test protocol regeneration with different templates"""
        # Step 1: Create completed job with transcript
        job_id = 'e2e_regen_job'
        
        temp_dir = tempfile.mkdtemp()
        transcript_file = os.path.join(temp_dir, 'regen_transcript.txt')
        summary_file = os.path.join(temp_dir, 'regen_summary.md')
        
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write("Test transcript for regeneration workflow.")
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self.test_protocol_content)
        
        job_data = {
            'job_id': job_id,
            'user_id': self.test_user_id,
            'filename': 'regen_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'transcript_file': transcript_file,
            'summary_file': summary_file
        }
        self.app.db_manager.create_job(job_data)
        
        # Step 2: Request protocol regeneration with different template
        with patch.object(self.app, 'generate_protocol_sync') as mock_generate:
            data = {'new_template': 'business'}
            
            response = self.client.post(f'/generate_protocol/{job_id}',
                                      data=data,
                                      headers=self.auth_headers)
            
            # Should redirect to new protocol job
            self.assertEqual(response.status_code, 302)
            self.assertIn('/status/', response.location)
            
            # Extract new job ID
            new_job_id = response.location.split('/status/')[-1]
            self.assertNotEqual(new_job_id, job_id)
            self.assertIn('protocol_business', new_job_id)
            
            # Verify new job was created
            new_job = self.app.db_manager.get_job_by_id(new_job_id, self.test_user_id)
            self.assertIsNotNone(new_job)
            self.assertEqual(new_job['template'], 'business')
            self.assertEqual(new_job['status'], 'processing')
            
            # Verify generate_protocol_sync was called
            mock_generate.assert_called_once()
        
        # Cleanup
        try:
            os.unlink(transcript_file)
            os.unlink(summary_file)
            os.rmdir(temp_dir)
        except:
            pass
    
    def test_user_isolation_workflow(self):
        """Test that user isolation works throughout the workflow"""
        # Step 1: Create second user
        user2_id = 'e2e_user_2'
        user2_data = {
            'user_id': user2_id,
            'email': 'e2e2@example.com',
            'name': 'E2E Test User 2'
        }
        self.app.db_manager.create_user(user2_data)
        
        user2_headers = {
            'X-Identity-Token': 'e2e_test_token_2',
            'X-User-Id': user2_id,
            'X-User-Email': 'e2e2@example.com',
            'X-User-Name': 'E2E Test User 2'
        }
        
        # Step 2: Create job for user 1
        job_id = 'e2e_isolation_job'
        job_data = {
            'job_id': job_id,
            'user_id': self.test_user_id,
            'filename': 'isolation_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        self.app.db_manager.create_job(job_data)
        
        # Step 3: User 2 tries to access user 1's job
        response = self.client.get(f'/status/{job_id}', headers=user2_headers)
        # Should be denied (redirect)
        self.assertEqual(response.status_code, 302)
        
        # Step 4: User 2 tries to access via API
        response = self.client.get(f'/api/status/{job_id}', headers=user2_headers)
        # Should be denied
        self.assertEqual(response.status_code, 404)
        
        # Step 5: User 2 tries to download files
        response = self.client.get(f'/download/{job_id}/transcript', headers=user2_headers)
        self.assertEqual(response.status_code, 302)  # Redirect due to access denied
        
        # Step 6: User 1 can still access their own job
        response = self.client.get(f'/status/{job_id}', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(f'/api/status/{job_id}', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
    
    def test_error_handling_workflow(self):
        """Test error handling throughout the workflow"""
        # Step 1: Test invalid file upload
        invalid_file = io.BytesIO(b'invalid content')
        data = {
            'file': (invalid_file, 'invalid_file.txt'),  # Wrong extension
            'template': 'standard'
        }
        
        response = self.client.post('/upload',
                                  data=data,
                                  headers=self.auth_headers,
                                  content_type='multipart/form-data')
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.location)
        
        # Step 2: Test accessing non-existent job
        response = self.client.get('/status/nonexistent_job', headers=self.auth_headers)
        self.assertEqual(response.status_code, 302)  # Redirect due to not found
        
        response = self.client.get('/api/status/nonexistent_job', headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)
        
        # Step 3: Test Confluence publication with incomplete job
        incomplete_job_id = 'e2e_incomplete_job'
        job_data = {
            'job_id': incomplete_job_id,
            'user_id': self.test_user_id,
            'filename': 'incomplete.mp3',
            'template': 'standard',
            'status': 'processing',  # Not completed
            'progress': 50
        }
        self.app.db_manager.create_job(job_data)
        
        publication_data = {
            'base_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/parent/',
            'page_title': 'Test',
            'space_key': 'TEST'
        }
        
        response = self.client.post(f'/publish_confluence/{incomplete_job_id}',
                                  data=publication_data,
                                  headers=self.auth_headers)
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    def test_statistics_and_monitoring_workflow(self):
        """Test statistics and monitoring functionality"""
        # Step 1: Create multiple jobs with different statuses
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
                'status': 'processing',
                'progress': 75
            },
            {
                'job_id': 'stats_job_3',
                'user_id': self.test_user_id,
                'filename': 'stats3.mp3',
                'template': 'project',
                'status': 'error',
                'progress': 0,
                'error': 'Processing failed'
            }
        ]
        
        for job_data in job_data_list:
            self.app.db_manager.create_job(job_data)
        
        # Step 2: Create Confluence publications
        publication_data_list = [
            {
                'job_id': 'stats_job_1',
                'confluence_page_id': 'stats_page_1',
                'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/1',
                'confluence_space_key': 'TEST',
                'page_title': '20250902 - Stats Test 1',
                'publication_status': PublicationStatus.PUBLISHED
            },
            {
                'job_id': 'stats_job_1',
                'confluence_page_id': 'stats_page_2',
                'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/2',
                'confluence_space_key': 'TEST',
                'page_title': '20250902 - Stats Test 1 (Retry)',
                'publication_status': PublicationStatus.FAILED,
                'error_message': 'Network error'
            }
        ]
        
        for pub_data in publication_data_list:
            self.app.db_manager.create_confluence_publication(pub_data)
        
        # Step 3: Test statistics page
        response = self.client.get('/statistics', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Statistics', response.data)
        
        # Step 4: Test health endpoint
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        health_data = json.loads(response.data)
        self.assertEqual(health_data['status'], 'healthy')
        self.assertIn('database', health_data)
        self.assertIn('confluence', health_data)
        
        # Verify database info
        self.assertGreaterEqual(health_data['database']['jobs_count'], 3)
        
        # Verify Confluence info
        self.assertTrue(health_data['confluence']['available'])
        self.assertTrue(health_data['confluence']['enabled'])
        
        # Step 5: Test jobs list
        response = self.client.get('/jobs', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        
        # Should show all user's jobs
        page_content = response.data.decode('utf-8')
        self.assertIn('stats1.mp3', page_content)
        self.assertIn('stats2.mp3', page_content)
        self.assertIn('stats3.mp3', page_content)
        self.assertIn('completed', page_content)
        self.assertIn('processing', page_content)
        self.assertIn('error', page_content)


class TestWorkflowPerformance(unittest.TestCase):
    """Performance tests for workflow operations"""
    
    def setUp(self):
        """Set up performance test environment"""
        # Create minimal test config
        self.test_config = {
            'database': {'path': ':memory:'},
            'auth': {'enabled': True, 'debug_mode': True},
            'confluence': {'enabled': False}  # Disable for performance testing
        }
        
        self.mock_api_keys = {
            'deepgram': {'api_key': 'test_key'},
            'claude': {'api_key': 'test_key'}
        }
        
        with patch('run_web.ConfigLoader.load_config') as mock_load_config, \
             patch('run_web.ConfigLoader.load_api_keys') as mock_load_api_keys, \
             patch('run_web.ConfigLoader.validate_api_keys') as mock_validate_keys:
            
            mock_load_config.return_value = self.test_config
            mock_load_api_keys.return_value = self.mock_api_keys
            mock_validate_keys.return_value = (True, True, 'test_key', 'test_key')
            
            self.app = WorkingMeetingWebApp('test_config.json')
            self.client = self.app.app.test_client()
        
        # Create test user
        self.test_user_id = 'perf_test_user'
        user_data = {
            'user_id': self.test_user_id,
            'email': 'perf@example.com',
            'name': 'Performance Test User'
        }
        self.app.db_manager.create_user(user_data)
        
        self.auth_headers = {
            'X-Identity-Token': 'perf_token',
            'X-User-Id': self.test_user_id,
            'X-User-Email': 'perf@example.com',
            'X-User-Name': 'Performance Test User'
        }
    
    def test_bulk_job_creation_performance(self):
        """Test performance of creating multiple jobs"""
        import time
        
        num_jobs = 50
        start_time = time.time()
        
        # Create multiple jobs
        for i in range(num_jobs):
            job_data = {
                'job_id': f'perf_job_{i}',
                'user_id': self.test_user_id,
                'filename': f'perf_test_{i}.mp3',
                'template': 'standard',
                'status': 'completed',
                'progress': 100
            }
            self.app.db_manager.create_job(job_data)
        
        creation_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 5 seconds)
        self.assertLess(creation_time, 5.0)
        
        # Verify all jobs were created
        user_jobs = self.app.db_manager.get_user_jobs(self.test_user_id)
        self.assertEqual(len(user_jobs), num_jobs)
        
        # Test jobs list page performance
        start_time = time.time()
        response = self.client.get('/jobs', headers=self.auth_headers)
        page_load_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        # Page should load quickly even with many jobs
        self.assertLess(page_load_time, 2.0)
    
    def test_api_response_performance(self):
        """Test API response performance"""
        import time
        
        # Create test job
        job_data = {
            'job_id': 'api_perf_job',
            'user_id': self.test_user_id,
            'filename': 'api_perf_test.mp3',
            'template': 'standard',
            'status': 'processing',
            'progress': 50,
            'message': 'Processing...'
        }
        self.app.db_manager.create_job(job_data)
        
        # Test API response time
        start_time = time.time()
        response = self.client.get('/api/status/api_perf_job', headers=self.auth_headers)
        api_response_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        # API should respond quickly
        self.assertLess(api_response_time, 0.5)
        
        # Verify response content
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'processing')
        self.assertEqual(data['progress'], 50)


if __name__ == '__main__':
    unittest.main()