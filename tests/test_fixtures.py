
#!/usr/bin/env python3
"""
Test fixtures and mock data for Confluence integration tests
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import PublicationStatus, JobStatus


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_user_data(user_id: str = "test_user", **kwargs) -> Dict[str, Any]:
        """Create test user data"""
        default_data = {
            'user_id': user_id,
            'email': f'{user_id}@example.com',
            'name': f'Test User {user_id}',
            'full_name': f'Test User {user_id} Full Name',
            'given_name': 'Test',
            'family_name': 'User',
            'preferred_username': user_id
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_job_data(job_id: str = "test_job", user_id: str = "test_user", **kwargs) -> Dict[str, Any]:
        """Create test job data"""
        default_data = {
            'job_id': job_id,
            'user_id': user_id,
            'filename': f'{job_id}.mp3',
            'template': 'standard',
            'status': JobStatus.COMPLETED,
            'progress': 100,
            'message': 'Processing completed successfully',
            'file_path': f'/tmp/{job_id}.mp3',
            'transcript_file': f'/tmp/{job_id}_transcript.txt',
            'summary_file': f'/tmp/{job_id}_summary.md',
            'created_at': datetime.utcnow().isoformat(),
            'completed_at': datetime.utcnow().isoformat(),
            'error': None,
            'original_job_id': None,
            'metadata': {}
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_confluence_publication_data(job_id: str = "test_job", **kwargs) -> Dict[str, Any]:
        """Create test Confluence publication data"""
        default_data = {
            'job_id': job_id,
            'confluence_page_id': f'page_{job_id}',
            'confluence_page_url': f'https://test.atlassian.net/wiki/spaces/TEST/pages/{job_id}',
            'confluence_space_key': 'TEST',
            'parent_page_id': None,
            'page_title': f'{datetime.now().strftime("%Y%m%d")} - Test Meeting Protocol',
            'publication_status': PublicationStatus.PUBLISHED,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'error_message': None,
            'retry_count': 0,
            'last_retry_at': None
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_confluence_config(**kwargs) -> Dict[str, Any]:
        """Create test Confluence configuration"""
        default_config = {
            'enabled': True,
            'base_url': 'https://test.atlassian.net/wiki',
            'username': 'test@example.com',
            'api_token': 'test_api_token_123',
            'space_key': 'TEST',
            'parent_page_id': None,
            'timeout': 30,
            'max_retries': 3,
            'retry_delay': 1.0,
            'auto_publish': False,
            'notification_settings': {
                'email_on_success': False,
                'email_on_failure': True
            },
            'advanced_settings': {
                'page_template': 'default',
                'content_format': 'storage',
                'enable_comments': True
            }
        }
        default_config.update(kwargs)
        return default_config
    
    @staticmethod
    def create_app_config(**kwargs) -> Dict[str, Any]:
        """Create test application configuration"""
        default_config = {
            'database': {
                'path': ':memory:',
                'timeout': 30,
                'check_same_thread': False
            },
            'auth': {
                'enabled': True,
                'debug_mode': True,
                'token_header': 'X-Identity-Token',
                'jwt_secret': 'test_secret_key_for_testing'
            },
            'confluence': TestDataFactory.create_confluence_config(),
            'settings': {
                'max_file_size_mb': 200,
                'deepgram_timeout_seconds': 300,
                'claude_model': 'claude-sonnet-4-20250514',
                'chunk_duration_minutes': 15
            },
            'supported_formats': {
                'audio': ['.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.opus'],
                'video': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm']
            },
            'template_examples': {
                'standard': 'Универсальный шаблон для любых встреч',
                'business': 'Официальный протокол для деловых встреч',
                'project': 'Фокус на управлении проектами и задачами',
                'standup': 'Краткий формат для ежедневных стендапов',
                'interview': 'Структурированный отчет об интервью'
            }
        }
        default_config.update(kwargs)
        return default_config
    
    @staticmethod
    def create_api_keys(**kwargs) -> Dict[str, Any]:
        """Create test API keys"""
        default_keys = {
            'deepgram': {
                'api_key': 'test_deepgram_api_key_12345'
            },
            'claude': {
                'api_key': 'test_claude_api_key_67890'
            }
        }
        default_keys.update(kwargs)
        return default_keys


class MockDataGenerator:
    """Generator for mock data and responses"""
    
    @staticmethod
    def create_meeting_protocol_content(topic: str = "Test Meeting", **kwargs) -> str:
        """Create realistic meeting protocol content"""
        date = kwargs.get('date', datetime.now().strftime('%Y-%m-%d'))
        participants = kwargs.get('participants', ['John Doe', 'Jane Smith', 'Bob Johnson'])
        decisions = kwargs.get('decisions', [
            'Implement new feature X',
            'Schedule follow-up meeting',
            'Review documentation'
        ])
        action_items = kwargs.get('action_items', [
            'John to prepare technical specification',
            'Jane to coordinate with stakeholders',
            'Bob to update project timeline'
        ])
        
        content = f"""# Meeting Protocol
Date: {date}
Topic: {topic}

## Participants
"""
        for participant in participants:
            content += f"- **{participant}**\n"
        
        content += f"""
## Discussion Points
1. Review of current project status
2. Discussion of {topic.lower()}
3. Planning for next phase
4. Resource allocation review

### Technical Details
```python
def process_meeting_data():
    # Process meeting information
    return {{
        'topic': '{topic}',
        'date': '{date}',
        'status': 'completed'
    }}
```

## Decisions Made
"""
        for i, decision in enumerate(decisions, 1):
            content += f"{i}. {decision}\n"
        
        content += """
## Action Items
"""
        for item in action_items:
            content += f"- [ ] {item}\n"
        
        content += f"""
## Next Steps
- Schedule follow-up meeting for next week
- Distribute meeting notes to all participants
- Begin implementation of decided actions

## Meeting Statistics
- Duration: 60 minutes
- Participants: {len(participants)}
- Decisions: {len(decisions)}
- Action Items: {len(action_items)}

---
*Meeting protocol generated automatically by Meeting Processor*
"""
        return content
    
    @staticmethod
    def create_transcript_content(duration_minutes: int = 30) -> str:
        """Create realistic transcript content"""
        content = f"""Meeting Transcript
Duration: {duration_minutes} minutes
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[00:00] John Doe: Good morning everyone, let's start today's meeting.

[00:30] Jane Smith: Thank you John. I'd like to begin with a review of our current project status.

[01:15] Bob Johnson: The development phase is progressing well. We've completed about 75% of the planned features.

[02:00] John Doe: That's excellent progress. What about the testing phase?

[02:30] Jane Smith: We're running parallel testing as features are completed. So far, we've identified and resolved 12 minor issues.

[03:45] Bob Johnson: The integration with the new API is working smoothly. Performance metrics are within expected ranges.

[05:00] John Doe: Great. Let's discuss the Confluence integration that we've been planning.

[05:30] Jane Smith: The Confluence integration is a key requirement for our documentation workflow.

[06:15] Bob Johnson: I've reviewed the technical specifications. The implementation should be straightforward.

[07:00] John Doe: What's our timeline for the Confluence integration?

[07:30] Jane Smith: Based on current progress, we should be able to complete it within two weeks.

[08:45] Bob Johnson: I agree with that timeline. We'll need to coordinate with the infrastructure team.

[10:00] John Doe: Perfect. Let's make sure we have proper testing in place.

[10:30] Jane Smith: Absolutely. We'll need comprehensive unit tests, integration tests, and end-to-end testing.

[12:00] Bob Johnson: I'll prepare a detailed test plan covering all scenarios.

[13:15] John Doe: Excellent. Any other topics we need to cover today?

[14:00] Jane Smith: We should discuss the security aspects of the integration.

[14:30] Bob Johnson: Good point. Token encryption and access control are critical.

[15:45] John Doe: Let's schedule a dedicated security review session.

[16:30] Jane Smith: I'll coordinate with the security team for that review.

[18:00] Bob Johnson: We should also consider performance testing under load.

[19:15] John Doe: Agreed. Let's include that in our test plan.

[20:00] Jane Smith: I think we've covered all the main points for today.

[20:30] Bob Johnson: Yes, we have a clear path forward.

[21:00] John Doe: Perfect. Let's wrap up and schedule our next meeting.

[End of transcript]
"""
        return content
    
    @staticmethod
    def create_confluence_api_responses() -> Dict[str, Any]:
        """Create mock Confluence API responses"""
        return {
            'create_page_success': {
                'id': '123456',
                'type': 'page',
                'status': 'current',
                'title': '20250902 - Test Meeting Protocol',
                'space': {
                    'id': 789,
                    'key': 'TEST',
                    'name': 'Test Space'
                },
                'version': {
                    'number': 1,
                    'when': datetime.utcnow().isoformat(),
                    'by': {
                        'type': 'known',
                        'username': 'test@example.com',
                        'displayName': 'Test User'
                    }
                },
                '_links': {
                    'webui': '/spaces/TEST/pages/123456',
                    'self': 'https://test.atlassian.net/wiki/rest/api/content/123456'
                }
            },
            'get_page_info': {
                'id': '123456',
                'type': 'page',
                'status': 'current',
                'title': '20250902 - Test Meeting Protocol',
                'space': {
                    'id': 789,
                    'key': 'TEST',
                    'name': 'Test Space'
                },
                'version': {
                    'number': 1
                },
                'ancestors': [
                    {
                        'id': '654321',
                        'title': 'Meeting Protocols'
                    }
                ]
            },
            'get_space_info': {
                'id': 789,
                'key': 'TEST',
                'name': 'Test Space',
                'type': 'global',
                'status': 'current',
                '_links': {
                    'webui': '/spaces/TEST',
                    'self': 'https://test.atlassian.net/wiki/rest/api/space/TEST'
                }
            },
            'search_pages': {
                'results': [
                    {
                        'id': '123456',
                        'title': '20250902 - Test Meeting Protocol',
                        'type': 'page',
                        'space': {
                            'key': 'TEST',
                            'name': 'Test Space'
                        }
                    },
                    {
                        'id': '789012',
                        'title': '20250901 - Previous Meeting',
                        'type': 'page',
                        'space': {
                            'key': 'TEST',
                            'name': 'Test Space'
                        }
                    }
                ],
                'size': 2,
                'totalSize': 2
            },
            'error_responses': {
                'unauthorized': {
                    'statusCode': 401,
                    'message': 'Unauthorized'
                },
                'forbidden': {
                    'statusCode': 403,
                    'message': 'Forbidden'
                },
                'not_found': {
                    'statusCode': 404,
                    'message': 'Page not found'
                },
                'server_error': {
                    'statusCode': 500,
                    'message': 'Internal server error'
                }
            }
        }


class TestEnvironmentSetup:
    """Helper class for setting up test environments"""
    
    @staticmethod
    def create_temp_files(file_contents: Dict[str, str]) -> Dict[str, str]:
        """Create temporary files with specified contents"""
        temp_files = {}
        
        for filename, content in file_contents.items():
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, 
                                                  suffix=f'_{filename}', encoding='utf-8')
            temp_file.write(content)
            temp_file.close()
            temp_files[filename] = temp_file.name
        
        return temp_files
    
    @staticmethod
    def cleanup_temp_files(file_paths: List[str]):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass
    
    @staticmethod
    def create_test_database_with_data(db_manager, num_users: int = 3, 
                                     num_jobs_per_user: int = 5,
                                     num_publications_per_job: int = 1) -> Dict[str, List[str]]:
        """Create test database with sample data"""
        created_data = {
            'users': [],
            'jobs': [],
            'publications': []
        }
        
        # Create users
        for i in range(num_users):
            user_data = TestDataFactory.create_user_data(f'test_user_{i}')
            db_manager.create_user(user_data)
            created_data['users'].append(user_data['user_id'])
            
            # Create jobs for each user
            for j in range(num_jobs_per_user):
                job_data = TestDataFactory.create_job_data(
                    f'test_job_{i}_{j}', 
                    user_data['user_id'],
                    status=JobStatus.COMPLETED if j % 2 == 0 else JobStatus.PROCESSING,
                    progress=100 if j % 2 == 0 else 50 + (j * 10)
                )
                db_manager.create_job(job_data)
                created_data['jobs'].append(job_data['job_id'])
                
                # Create publications for completed jobs
                if job_data['status'] == JobStatus.COMPLETED:
                    for k in range(num_publications_per_job):
                        pub_data = TestDataFactory.create_confluence_publication_data(
                            job_data['job_id'],
                            confluence_page_id=f'page_{i}_{j}_{k}',
                            publication_status=PublicationStatus.PUBLISHED if k == 0 else PublicationStatus.FAILED
                        )
                        publication = db_manager.create_confluence_publication(pub_data)
                        created_data['publications'].append(publication['id'])
        
        return created_data


class MockConfluenceClient:
    """Mock Confluence client for testing"""
    
    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        self.responses = responses or MockDataGenerator.create_confluence_api_responses()
        self.call_history = []
    
    def test_connection(self) -> bool:
        """Mock test connection"""
        self.call_history.append(('test_connection', {}))
        return True
    
    def create_page(self, title: str, content: str, parent_page_id: Optional[str] = None,
                   space_key: Optional[str] = None) -> Dict[str, Any]:
        """Mock create page"""
        self.call_history.append(('create_page', {
            'title': title,
            'content': content,
            'parent_page_id': parent_page_id,
            'space_key': space_key
        }))
        
        response = self.responses['create_page_success'].copy()
        response['title'] = title
        return response
    
    def get_page_info(self, page_id: str) -> Dict[str, Any]:
        """Mock get page info"""
        self.call_history.append(('get_page_info', {'page_id': page_id}))
        return self.responses['get_page_info']
    
    def get_space_info(self, space_key: Optional[str] = None) -> Dict[str, Any]:
        """Mock get space info"""
        self.call_history.append(('get_space_info', {'space_key': space_key}))
        return self.responses['get_space_info']
    
    def search_pages(self, query: str, space_key: Optional[str] = None, 
                    limit: int = 25) -> List[Dict[str, Any]]:
        """Mock search pages"""
        self.call_history.append(('search_pages', {
            'query': query,
            'space_key': space_key,
            'limit': limit
        }))
        return self.responses['search_pages']['results']
    
    def update_page(self, page_id: str, title: str, content: str, 
                   version_number: int) -> Dict[str, Any]:
        """Mock update page"""
        self.call_history.append(('update_page', {
            'page_id': page_id,
            'title': title,
            'content': content,
            'version_number': version_number
        }))
        
        response = self.responses['create_page_success'].copy()
        response['id'] = page_id
        response['title'] = title
        response['version']['number'] = version_number + 1
        return response
    
    def delete_page(self, page_id: str) -> bool:
        """Mock delete page"""
        self.call_history.append(('delete_page', {'page_id': page_id}))
        return True


class TestAssertions:
    """Custom assertions for testing"""
    
    @staticmethod
    def assert_confluence_publication_valid(publication: Dict[str, Any]):
        """Assert that a Confluence publication is valid"""
        required_fields = [
            'job_id', 'confluence_page_id', 'confluence_page_url',
            'confluence_space_key', 'page_title', 'publication_status'
        ]
        
        for field in required_fields:
            assert field in publication, f"Missing required field: {field}"
            assert publication[field] is not None, f"Field {field} is None"
            assert publication[field] != '', f"Field {field} is empty"
    
    @staticmethod
    def assert_job_data_valid(job: Dict[str, Any]):
        """Assert that job data is valid"""
        required_fields = ['job_id', 'user_id', 'filename', 'status']
        
        for field in required_fields:
            assert field in job, f"Missing required field: {field}"
            assert job[field] is not None, f"Field {field} is None"
            assert job[field] != '', f"Field {field} is empty"
        
        # Validate status
        assert job['status'] in [status.value for status in JobStatus], \
            f"Invalid job status: {job['status']}"
        
        # Validate progress
        if 'progress' in job:
            assert 0 <= job['progress'] <= 100, \
                f"Invalid progress value: {job['progress']}"
    
    @staticmethod
    def assert_user_data_valid(user: Dict[str, Any]):
        """Assert that user data is valid"""
        required_fields = ['user_id', 'email']
        
        for field in required_fields:
            assert field in user, f"Missing required field: {field}"
            assert user[field] is not None, f"Field {field} is None"
            assert user[field] != '', f"Field {field} is empty"
        
        # Validate email format
        assert '@' in user['email'], f"Invalid email format: {user['email']}"
    
    @staticmethod
    def assert_confluence_config_valid(config: Dict[str, Any]):
        """Assert that Confluence configuration is valid"""
        required_fields = ['base_url', 'username', 'api_token', 'space_key']
        
        for field in required_fields:
            assert field in config, f"Missing required field: {field}"
            assert config[field] is not None, f"Field {field} is None"
            assert config[field] != '', f"Field {field} is empty"
        
        # Validate URL format
        assert config['base_url'].startswith(('http://', 'https://')), \
            f"Invalid base_url format: {config['base_url']}"
    
    @staticmethod
    def assert_api_response_structure(response: Dict[str, Any], expected_fields: List[str]):
        """Assert that API response has expected structure"""
        for field in expected_fields:
            assert field in response, f"Missing field in API response: {field}"
    
    @staticmethod
    def assert_database_integrity(db_manager, expected_counts: Dict[str, int]):
        """Assert database integrity with expected record counts"""
        for table, expected_count in expected_counts.items():
            if table == 'users':
                actual_count = len(db_manager.get_all_users())
            elif table == 'jobs':
                actual_count = len(db_manager.get_all_jobs())
            elif table == 'publications':
                actual_count = len(db_manager.get_all_confluence_publications())
            else:
                raise ValueError(f"Unknown table: {table}")
            
            assert actual_count == expected_count, \
                f"Expected {expected_count} {table}, got {actual_count}"


class PerformanceTestData:
    """Data generators for performance testing"""
    
    @staticmethod
    def generate_large_content(size_kb: int = 100) -> str:
        """Generate large content for performance testing"""
        base_content = MockDataGenerator.create_meeting_protocol_content()
        
        # Calculate how many times to repeat to reach target size
        base_size = len(base_content.encode('utf-8'))
        repeat_count = max(1, (size_kb * 1024) // base_size)
        
        large_content = base_content
        for i in range(repeat_count - 1):
            large_content += f"\n\n## Additional Section {i+1}\n"
            large_content += base_content
        
        return large_content
    
    @staticmethod
    def generate_bulk_test_data(num_users: int = 100, 
                              num_jobs_per_user: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """Generate bulk test data for performance testing"""
        test_data = {
            'users': [],
            'jobs': [],
            'publications': []
        }
        
        for i in range(num_users):
            user_data = TestDataFactory.create_user_data(f'perf_user_{i}')
            test_data['users'].append(user_data)
            
            for j in range(num_jobs_per_user):
                job_data = TestDataFactory.create_job_data(
                    f'perf_job_{i}_{j}',
                    user_data['user_id'],
                    status=JobStatus.COMPLETED if j % 3 == 0 else JobStatus.PROCESSING
                )
                test_data['jobs'].append(job_data)
                
                # Add publication for some completed jobs
                if job_data['status'] == JobStatus.COMPLETED and j % 5 == 0:
                    pub_data = TestDataFactory.create_confluence_publication_data(
                        job_data['job_id'],
                        confluence_page_id=f'perf_page_{i}_{j}'
                    )
                    test_data['publications'].append(pub_data)
        
        return test_data
    
    @staticmethod
    def create_concurrent_test_scenarios() -> List[Dict[str, Any]]:
        """Create scenarios for concurrent testing"""
        scenarios = [
            {
                'name': 'concurrent_job_creation',
                'description': 'Multiple users creating jobs simultaneously',
                'concurrent_users': 10,
                'operations_per_user': 5,
                'operation_type': 'create_job'
            },
            {
                'name': 'concurrent_publication',
                'description': 'Multiple users publishing to Confluence simultaneously',
                'concurrent_users': 5,
                'operations_per_user': 3,
                'operation_type': 'publish_to_confluence'
            },
            {
                'name': 'mixed_operations',
                'description': 'Mixed read/write operations under load',
                'concurrent_users': 15,
                'operations_per_user': 10,
                'operation_type': 'mixed'
            },
            {
                'name': 'database_stress',
                'description': 'Heavy database operations',
                'concurrent_users': 20,
                'operations_per_user': 20,
                'operation_type': 'database_intensive'
            }
        ]
        return scenarios


class SecurityTestData:
    """Data for security testing"""
    
    @staticmethod
    def create_malicious_inputs() -> Dict[str, List[str]]:
        """Create malicious inputs for security testing"""
        return {
            'sql_injection': [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "'; UPDATE users SET password='hacked'; --",
                "' UNION SELECT * FROM users --"
            ],
            'xss_payloads': [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "<img src=x onerror=alert('XSS')>",
                "';alert('XSS');//"
            ],
            'path_traversal': [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "....//....//....//etc/passwd",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
            ],
            'command_injection': [
                "; ls -la",
                "| cat /etc/passwd",
                "&& rm -rf /",
                "`whoami`"
            ],
            'oversized_inputs': [
                "A" * 10000,  # Very long string
                "🚀" * 5000,  # Unicode characters
                "\x00" * 1000,  # Null bytes
                "\n" * 1000   # Newlines
            ]
        }
    
    @staticmethod
    def create_invalid_tokens() -> List[str]:
        """Create invalid JWT tokens for testing"""
        return [
            "",  # Empty token
            "invalid.token.format",  # Invalid format
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",  # Invalid signature
            "expired.token.here",  # Expired token placeholder
            "malformed",  # Malformed token
            "Bearer invalid_token",  # Invalid Bearer format
            "null",  # Null string
            "undefined"  # Undefined string
        ]
    
    @staticmethod
    def create_encryption_test_data() -> Dict[str, Any]:
        """Create data for encryption testing"""
        return {
            'test_strings': [
                "simple_api_token",
                "complex_token_with_special_chars!@#$%^&*()",
                "very_long_token_" + "x" * 1000,
                "unicode_token_🔐🚀💻",
                "",  # Empty string
                " ",  # Whitespace
                "\n\t\r",  # Control characters
            ],
            'key_sizes': [16, 24, 32],  # Different key sizes for testing
            'iterations': 1000,  # Number of encryption/decryption cycles
            'timing_attack_samples': 10000  # Samples for timing attack testing
        }


# Export all classes and functions for easy importing
__all__ = [
    'TestDataFactory',
    'MockDataGenerator', 
    'TestEnvironmentSetup',
    'MockConfluenceClient',
    'TestAssertions',
    'PerformanceTestData',
    'SecurityTestData'
]


if __name__ == '__main__':
    # Example usage and testing of fixtures
    print("Testing fixture creation...")
    
    # Test data factory
    user_data = TestDataFactory.create_user_data()
    job_data = TestDataFactory.create_job_data()
    pub_data = TestDataFactory.create_confluence_publication_data()
    
    print(f"Created user: {user_data['user_id']}")
    print(f"Created job: {job_data['job_id']}")
    print(f"Created publication: {pub_data['confluence_page_id']}")
    
    # Test mock data generator
    content = MockDataGenerator.create_meeting_protocol_content()
    print(f"Generated content length: {len(content)} characters")
    
    # Test mock client
    mock_client = MockConfluenceClient()
    response = mock_client.create_page("Test Page", content)
    print(f"Mock client response: {response['id']}")
    
    # Test assertions
    try:
        TestAssertions.assert_user_data_valid(user_data)
        TestAssertions.assert_job_data_valid(job_data)
        TestAssertions.assert_confluence_publication_valid(pub_data)
        print("All assertions passed!")
    except AssertionError as e:
        print(f"Assertion failed: {e}")
    
    print("Fixture testing completed successfully!")