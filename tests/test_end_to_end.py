
#!/usr/bin/env python3
"""
End-to-end workflow tests for the complete Confluence publication workflow
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import gc
import tempfile
import os
import sys
import json
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
                'debug_mode': False,  # Requests are authenticated through the token validator
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
        
        # Mock ConfigLoader.
        # AUTH_DEBUG_MODE from a local .env overrides config, so pin it for app creation.
        with patch.dict(os.environ, {'AUTH_DEBUG_MODE': 'false'}), \
             patch('run_web.ConfigLoader.load_config') as mock_load_config, \
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

        # Requests are made as the test user unless a test switches with as_user()
        self.auth_headers = {'X-Identity-Token': 'e2e_test_token'}
        default_user = self.as_user(self.test_user_data)
        default_user.start()
        self.addCleanup(default_user.stop)

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
        # Open sqlite3 connections keep the database file locked on Windows
        self.app.executor.shutdown(wait=True)
        self.client = None
        self.app = None
        gc.collect()
        for path in (self.test_db.name, self.config_file.name, self.api_keys_file.name):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass

    def as_user(self, user_data):
        """Patcher that makes the token validator accept requests as the given user"""
        return patch.object(self.app.token_validator, 'validate_request',
                            return_value=(True, dict(user_data), None))

    def publish_to_confluence(self, job_id, mock_client_instance):
        """Posts the job's protocol to /publish_confluence as an AJAX request"""
        metadata = {
            'page_id': '111',
            'space_key': 'TEST',
            'page_title': 'Parent page',
            'extraction_method': 'test'
        }
        headers = dict(self.auth_headers, **{'X-Requested-With': 'XMLHttpRequest'})

        with patch.object(self.app, 'extract_confluence_metadata', return_value=metadata), \
             patch('confluence_client.ConfluenceServerClient', return_value=mock_client_instance):
            return self.client.post(
                f'/publish_confluence/{job_id}',
                data={
                    'base_page_url': 'https://wiki.example.com/pages/viewpage.action?pageId=111',
                    'page_title': '20250902 - E2E Test Meeting'
                },
                headers=headers
            )

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
        self.assertIn(b'e2e_test_meeting.mp3', response.data)

        response = self.client.get(f'/api/status/{job_id}', headers=self.auth_headers)
        self.assertEqual(json.loads(response.data)['stage'], 'completed')
        
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
    
    def test_complete_confluence_publication_workflow(self):
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

        # Step 3: Publish to Confluence
        response = self.publish_to_confluence(job_id, mock_client_instance)

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
    
    def test_confluence_publication_failure_and_retry_workflow(self):
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

        # Step 3: Attempt publication (should fail); AJAX errors are reported in the JSON body
        response = self.publish_to_confluence(job_id, mock_client_instance)

        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('Network timeout', response_data['error'])

        # Step 4: Nothing was published
        publications = self.app.db_manager.get_confluence_publications_by_job_id(job_id)
        self.assertFalse([p for p in publications
                          if p['publication_status'] == PublicationStatus.PUBLISHED])

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
        response = self.publish_to_confluence(job_id, mock_client_instance)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])

        # Step 7: Verify successful publication was saved
        publications = self.app.db_manager.get_confluence_publications_by_job_id(job_id)

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
        
        user2_headers = {'X-Identity-Token': 'e2e_test_token_2'}

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
        
        with self.as_user(user2_data):
            # Step 3: User 2 tries to access user 1's job
            response = self.client.get(f'/status/{job_id}', headers=user2_headers)
            # Should be denied (redirect)
            self.assertEqual(response.status_code, 302)

            # Step 4: User 2 tries to access via API
            response = self.client.get(f'/api/status/{job_id}', headers=user2_headers)
            # Should be denied
            self.assertEqual(response.status_code, 404)

            # Step 5: Direct result links are public; this job has no transcript file
            response = self.client.get(f'/download/{job_id}/transcript', headers=user2_headers)
            self.assertEqual(response.status_code, 404)

            # User 2 does not see user 1's job in the list
            response = self.client.get('/jobs', headers=user2_headers)
            self.assertNotIn(b'isolation_test.mp3', response.data)

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
        self.assertIn('Статистика'.encode('utf-8'), response.data)
        
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
        # Statuses are rendered as Russian badges
        self.assertIn('Транскрибация готова', page_content)
        self.assertNotIn('table-responsive', page_content)
        self.assertIn('Транскрибация', page_content)
        self.assertIn('Ошибка транскрибации', page_content)


if __name__ == '__main__':
    unittest.main()