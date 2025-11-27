
#!/usr/bin/env python3
"""
Comprehensive unit tests for database models
"""

import unittest
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import (
    User, Job, ConfluencePublication, PublicationStatus, JobStatus,
    DatabaseSchema, DatabaseValidator
)


class TestUser(unittest.TestCase):
    """Test cases for User model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'name': 'Test User',
            'full_name': 'Test Full User',
            'given_name': 'Test',
            'family_name': 'User',
            'preferred_username': 'testuser'
        }
    
    def test_user_creation(self):
        """Test User object creation"""
        user = User(**self.test_user_data)
        
        self.assertEqual(user.user_id, 'test_user_123')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.name, 'Test User')
        self.assertEqual(user.full_name, 'Test Full User')
        self.assertEqual(user.given_name, 'Test')
        self.assertEqual(user.family_name, 'User')
        self.assertEqual(user.preferred_username, 'testuser')
        self.assertIsInstance(user.created_at, datetime)
        self.assertIsNone(user.last_login)
    
    def test_user_creation_minimal(self):
        """Test User creation with minimal data"""
        user = User(user_id='minimal_user')
        
        self.assertEqual(user.user_id, 'minimal_user')
        self.assertIsNone(user.email)
        self.assertIsNone(user.name)
        self.assertIsInstance(user.created_at, datetime)
    
    def test_user_to_dict(self):
        """Test User serialization to dictionary"""
        user = User(**self.test_user_data)
        user_dict = user.to_dict()
        
        self.assertEqual(user_dict['user_id'], 'test_user_123')
        self.assertEqual(user_dict['email'], 'test@example.com')
        self.assertEqual(user_dict['name'], 'Test User')
        self.assertIsInstance(user_dict['created_at'], str)
        self.assertIsNone(user_dict['last_login'])
    
    def test_user_from_dict(self):
        """Test User deserialization from dictionary"""
        user = User(**self.test_user_data)
        user_dict = user.to_dict()
        
        restored_user = User.from_dict(user_dict)
        
        self.assertEqual(restored_user.user_id, user.user_id)
        self.assertEqual(restored_user.email, user.email)
        self.assertEqual(restored_user.name, user.name)
        self.assertEqual(restored_user.full_name, user.full_name)
    
    def test_user_datetime_handling(self):
        """Test datetime handling in User model"""
        # Test with ISO format datetime
        test_data = self.test_user_data.copy()
        test_data['created_at'] = '2025-09-02T12:00:00+00:00'
        test_data['last_login'] = '2025-09-02T13:00:00Z'
        
        user = User.from_dict(test_data)
        
        self.assertIsInstance(user.created_at, datetime)
        self.assertIsInstance(user.last_login, datetime)
    
    def test_user_invalid_datetime(self):
        """Test handling of invalid datetime strings"""
        test_data = self.test_user_data.copy()
        test_data['created_at'] = 'invalid_datetime'
        test_data['last_login'] = 'also_invalid'
        
        user = User.from_dict(test_data)
        
        # Should fallback to current time for created_at
        self.assertIsInstance(user.created_at, datetime)
        # Should be None for invalid last_login
        self.assertIsNone(user.last_login)


class TestJob(unittest.TestCase):
    """Test cases for Job model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_job_data = {
            'job_id': 'job_123',
            'user_id': 'user_123',
            'filename': 'test_meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100,
            'message': 'Processing completed',
            'file_path': '/path/to/file.mp3',
            'transcript_file': '/path/to/transcript.txt',
            'summary_file': '/path/to/summary.md',
            'error': None,
            'original_job_id': 'original_123',
            'metadata': {'key': 'value'}
        }
    
    def test_job_creation(self):
        """Test Job object creation"""
        job = Job(**self.test_job_data)
        
        self.assertEqual(job.job_id, 'job_123')
        self.assertEqual(job.user_id, 'user_123')
        self.assertEqual(job.filename, 'test_meeting.mp3')
        self.assertEqual(job.template, 'standard')
        self.assertEqual(job.status, 'completed')
        self.assertEqual(job.progress, 100)
        self.assertEqual(job.message, 'Processing completed')
        self.assertEqual(job.file_path, '/path/to/file.mp3')
        self.assertEqual(job.transcript_file, '/path/to/transcript.txt')
        self.assertEqual(job.summary_file, '/path/to/summary.md')
        self.assertIsNone(job.error)
        self.assertEqual(job.original_job_id, 'original_123')
        self.assertEqual(job.metadata, {'key': 'value'})
        self.assertIsInstance(job.created_at, datetime)
    
    def test_job_creation_minimal(self):
        """Test Job creation with minimal required data"""
        job = Job(
            job_id='minimal_job',
            user_id='user_123',
            filename='test.mp3',
            template='standard'
        )
        
        self.assertEqual(job.job_id, 'minimal_job')
        self.assertEqual(job.status, 'uploaded')
        self.assertEqual(job.progress, 0)
        self.assertEqual(job.message, '')
        self.assertEqual(job.metadata, {})
    
    def test_job_status_methods(self):
        """Test Job status checking methods"""
        # Test completed job
        completed_job = Job(
            job_id='completed',
            user_id='user_123',
            filename='test.mp3',
            template='standard',
            status='completed'
        )
        
        self.assertTrue(completed_job.is_completed())
        self.assertFalse(completed_job.is_failed())
        self.assertFalse(completed_job.is_processing())
        
        # Test failed job
        failed_job = Job(
            job_id='failed',
            user_id='user_123',
            filename='test.mp3',
            template='standard',
            status='error'
        )
        
        self.assertFalse(failed_job.is_completed())
        self.assertTrue(failed_job.is_failed())
        self.assertFalse(failed_job.is_processing())
        
        # Test processing job
        processing_job = Job(
            job_id='processing',
            user_id='user_123',
            filename='test.mp3',
            template='standard',
            status='processing'
        )
        
        self.assertFalse(processing_job.is_completed())
        self.assertFalse(processing_job.is_failed())
        self.assertTrue(processing_job.is_processing())
    
    def test_job_to_dict(self):
        """Test Job serialization to dictionary"""
        job = Job(**self.test_job_data)
        job_dict = job.to_dict()
        
        self.assertEqual(job_dict['job_id'], 'job_123')
        self.assertEqual(job_dict['user_id'], 'user_123')
        self.assertEqual(job_dict['filename'], 'test_meeting.mp3')
        self.assertEqual(job_dict['template'], 'standard')
        self.assertEqual(job_dict['status'], 'completed')
        self.assertEqual(job_dict['progress'], 100)
        self.assertEqual(job_dict['metadata'], {'key': 'value'})
        self.assertIsInstance(job_dict['created_at'], str)
    
    def test_job_from_dict(self):
        """Test Job deserialization from dictionary"""
        job = Job(**self.test_job_data)
        job_dict = job.to_dict()
        
        restored_job = Job.from_dict(job_dict)
        
        self.assertEqual(restored_job.job_id, job.job_id)
        self.assertEqual(restored_job.user_id, job.user_id)
        self.assertEqual(restored_job.filename, job.filename)
        self.assertEqual(restored_job.template, job.template)
        self.assertEqual(restored_job.status, job.status)
        self.assertEqual(restored_job.progress, job.progress)
        self.assertEqual(restored_job.metadata, job.metadata)
    
    def test_job_metadata_handling(self):
        """Test metadata handling in Job model"""
        # Test with string JSON metadata
        test_data = self.test_job_data.copy()
        test_data['metadata'] = '{"test": "value"}'
        
        job = Job.from_dict(test_data)
        self.assertEqual(job.metadata, {"test": "value"})
        
        # Test with invalid JSON metadata
        test_data['metadata'] = 'invalid_json'
        job = Job.from_dict(test_data)
        self.assertEqual(job.metadata, {})


class TestConfluencePublication(unittest.TestCase):
    """Test cases for ConfluencePublication model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_publication_data = {
            'id': 1,
            'job_id': 'job_123',
            'confluence_page_id': 'page_456',
            'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/456',
            'confluence_space_key': 'TEST',
            'parent_page_id': 'parent_789',
            'page_title': '20250902 - Test Meeting',
            'publication_status': PublicationStatus.PUBLISHED,
            'error_message': None,
            'retry_count': 0
        }
    
    def test_confluence_publication_creation(self):
        """Test ConfluencePublication object creation"""
        publication = ConfluencePublication(**self.test_publication_data)
        
        self.assertEqual(publication.id, 1)
        self.assertEqual(publication.job_id, 'job_123')
        self.assertEqual(publication.confluence_page_id, 'page_456')
        self.assertEqual(publication.confluence_page_url, 'https://test.atlassian.net/wiki/spaces/TEST/pages/456')
        self.assertEqual(publication.confluence_space_key, 'TEST')
        self.assertEqual(publication.parent_page_id, 'parent_789')
        self.assertEqual(publication.page_title, '20250902 - Test Meeting')
        self.assertEqual(publication.publication_status, PublicationStatus.PUBLISHED)
        self.assertIsNone(publication.error_message)
        self.assertEqual(publication.retry_count, 0)
        self.assertIsInstance(publication.created_at, datetime)
        self.assertIsInstance(publication.updated_at, datetime)
    
    def test_confluence_publication_minimal(self):
        """Test ConfluencePublication creation with minimal data"""
        publication = ConfluencePublication(
            job_id='minimal_job',
            confluence_page_id='page_123',
            confluence_page_url='https://test.atlassian.net/wiki/spaces/TEST/pages/123',
            confluence_space_key='TEST',
            page_title='Test Page'
        )
        
        self.assertEqual(publication.job_id, 'minimal_job')
        self.assertEqual(publication.publication_status, PublicationStatus.PUBLISHED)
        self.assertEqual(publication.retry_count, 0)
        self.assertIsNone(publication.error_message)
    
    def test_confluence_publication_status_methods(self):
        """Test ConfluencePublication status checking methods"""
        # Test published publication
        published = ConfluencePublication(
            job_id='job_1',
            confluence_page_id='page_1',
            confluence_page_url='https://test.atlassian.net/wiki/spaces/TEST/pages/1',
            confluence_space_key='TEST',
            page_title='Published Page',
            publication_status=PublicationStatus.PUBLISHED
        )
        
        self.assertTrue(published.is_published())
        self.assertFalse(published.is_failed())
        self.assertFalse(published.is_retrying())
        
        # Test failed publication
        failed = ConfluencePublication(
            job_id='job_2',
            confluence_page_id='page_2',
            confluence_page_url='https://test.atlassian.net/wiki/spaces/TEST/pages/2',
            confluence_space_key='TEST',
            page_title='Failed Page',
            publication_status=PublicationStatus.FAILED
        )
        
        self.assertFalse(failed.is_published())
        self.assertTrue(failed.is_failed())
        self.assertFalse(failed.is_retrying())
        
        # Test retrying publication
        retrying = ConfluencePublication(
            job_id='job_3',
            confluence_page_id='page_3',
            confluence_page_url='https://test.atlassian.net/wiki/spaces/TEST/pages/3',
            confluence_space_key='TEST',
            page_title='Retrying Page',
            publication_status=PublicationStatus.RETRYING
        )
        
        self.assertFalse(retrying.is_published())
        self.assertFalse(retrying.is_failed())
        self.assertTrue(retrying.is_retrying())
    
    def test_confluence_publication_retry_increment(self):
        """Test retry count increment functionality"""
        publication = ConfluencePublication(**self.test_publication_data)
        
        initial_retry_count = publication.retry_count
        initial_last_retry = publication.last_retry_at
        
        publication.increment_retry_count()
        
        self.assertEqual(publication.retry_count, initial_retry_count + 1)
        self.assertIsNotNone(publication.last_retry_at)
        self.assertNotEqual(publication.last_retry_at, initial_last_retry)
    
    def test_confluence_publication_to_dict(self):
        """Test ConfluencePublication serialization to dictionary"""
        publication = ConfluencePublication(**self.test_publication_data)
        publication_dict = publication.to_dict()
        
        self.assertEqual(publication_dict['id'], 1)
        self.assertEqual(publication_dict['job_id'], 'job_123')
        self.assertEqual(publication_dict['confluence_page_id'], 'page_456')
        self.assertEqual(publication_dict['confluence_page_url'], 'https://test.atlassian.net/wiki/spaces/TEST/pages/456')
        self.assertEqual(publication_dict['confluence_space_key'], 'TEST')
        self.assertEqual(publication_dict['page_title'], '20250902 - Test Meeting')
        self.assertEqual(publication_dict['publication_status'], PublicationStatus.PUBLISHED)
        self.assertEqual(publication_dict['retry_count'], 0)
        self.assertIsInstance(publication_dict['created_at'], str)
        self.assertIsInstance(publication_dict['updated_at'], str)
    
    def test_confluence_publication_from_dict(self):
        """Test ConfluencePublication deserialization from dictionary"""
        publication = ConfluencePublication(**self.test_publication_data)
        publication_dict = publication.to_dict()
        
        restored_publication = ConfluencePublication.from_dict(publication_dict)
        
        self.assertEqual(restored_publication.id, publication.id)
        self.assertEqual(restored_publication.job_id, publication.job_id)
        self.assertEqual(restored_publication.confluence_page_id, publication.confluence_page_id)
        self.assertEqual(restored_publication.confluence_page_url, publication.confluence_page_url)
        self.assertEqual(restored_publication.confluence_space_key, publication.confluence_space_key)
        self.assertEqual(restored_publication.page_title, publication.page_title)
        self.assertEqual(restored_publication.publication_status, publication.publication_status)
        self.assertEqual(restored_publication.retry_count, publication.retry_count)


class TestDatabaseSchema(unittest.TestCase):
    """Test cases for DatabaseSchema"""
    
    def test_get_create_tables_sql(self):
        """Test SQL generation for table creation"""
        sql_statements = DatabaseSchema.get_create_tables_sql()
        
        self.assertIsInstance(sql_statements, list)
        self.assertGreater(len(sql_statements), 0)
        
        # Check that all expected tables are created
        sql_text = ' '.join(sql_statements)
        self.assertIn('CREATE TABLE IF NOT EXISTS users', sql_text)
        self.assertIn('CREATE TABLE IF NOT EXISTS jobs', sql_text)
        self.assertIn('CREATE TABLE IF NOT EXISTS confluence_publications', sql_text)
    
    def test_get_create_indexes_sql(self):
        """Test SQL generation for index creation"""
        sql_statements = DatabaseSchema.get_create_indexes_sql()
        
        self.assertIsInstance(sql_statements, list)
        self.assertGreater(len(sql_statements), 0)
        
        # Check that indexes are created for important columns
        sql_text = ' '.join(sql_statements)
        self.assertIn('idx_jobs_user_id', sql_text)
        self.assertIn('idx_jobs_status', sql_text)
        self.assertIn('idx_confluence_publications_job_id', sql_text)
        self.assertIn('idx_confluence_publications_status', sql_text)
    
    def test_get_migration_sql(self):
        """Test migration SQL generation"""
        # Test migration version 1 (initial schema)
        migration_1 = DatabaseSchema.get_migration_sql(1)
        self.assertIsInstance(migration_1, list)
        self.assertGreater(len(migration_1), 0)
        
        # Test migration version 2 (indexes)
        migration_2 = DatabaseSchema.get_migration_sql(2)
        self.assertIsInstance(migration_2, list)
        self.assertGreater(len(migration_2), 0)
        
        # Test migration version 3 (confluence integration)
        migration_3 = DatabaseSchema.get_migration_sql(3)
        self.assertIsInstance(migration_3, list)
        self.assertGreater(len(migration_3), 0)
        
        # Check that confluence_publications table is in migration 3
        sql_text = ' '.join(migration_3)
        self.assertIn('confluence_publications', sql_text)
        self.assertIn('TRIGGER', sql_text)  # Should include update trigger
        
        # Test non-existent migration version
        migration_999 = DatabaseSchema.get_migration_sql(999)
        self.assertEqual(migration_999, [])


class TestDatabaseValidator(unittest.TestCase):
    """Test cases for DatabaseValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        
        self.valid_job_data = {
            'job_id': 'job_123',
            'user_id': 'user_123',
            'filename': 'test_meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        
        self.valid_publication_data = {
            'job_id': 'job_123',
            'confluence_page_id': 'page_456',
            'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/456',
            'confluence_space_key': 'TEST',
            'page_title': '20250902 - Test Meeting',
            'publication_status': PublicationStatus.PUBLISHED,
            'retry_count': 0
        }
    
    def test_validate_user_data_valid(self):
        """Test user data validation with valid data"""
        self.assertTrue(DatabaseValidator.validate_user_data(self.valid_user_data))
    
    def test_validate_user_data_invalid(self):
        """Test user data validation with invalid data"""
        # Missing user_id
        invalid_data = self.valid_user_data.copy()
        del invalid_data['user_id']
        self.assertFalse(DatabaseValidator.validate_user_data(invalid_data))
        
        # Empty user_id
        invalid_data = self.valid_user_data.copy()
        invalid_data['user_id'] = ''
        self.assertFalse(DatabaseValidator.validate_user_data(invalid_data))
        
        # Non-string user_id
        invalid_data = self.valid_user_data.copy()
        invalid_data['user_id'] = 123
        self.assertFalse(DatabaseValidator.validate_user_data(invalid_data))
        
        # Invalid email type
        invalid_data = self.valid_user_data.copy()
        invalid_data['email'] = 123
        self.assertFalse(DatabaseValidator.validate_user_data(invalid_data))
    
    def test_validate_job_data_valid(self):
        """Test job data validation with valid data"""
        self.assertTrue(DatabaseValidator.validate_job_data(self.valid_job_data))
    
    def test_validate_job_data_invalid(self):
        """Test job data validation with invalid data"""
        # Missing required fields
        for field in ['job_id', 'user_id', 'filename', 'template']:
            invalid_data = self.valid_job_data.copy()
            del invalid_data[field]
            self.assertFalse(DatabaseValidator.validate_job_data(invalid_data))
        
        # Invalid status
        invalid_data = self.valid_job_data.copy()
        invalid_data['status'] = 'invalid_status'
        self.assertFalse(DatabaseValidator.validate_job_data(invalid_data))
        
        # Invalid progress
        invalid_data = self.valid_job_data.copy()
        invalid_data['progress'] = 150  # > 100
        self.assertFalse(DatabaseValidator.validate_job_data(invalid_data))
        
        invalid_data['progress'] = -10  # < 0
        self.assertFalse(DatabaseValidator.validate_job_data(invalid_data))
        
        invalid_data['progress'] = 'not_a_number'
        self.assertFalse(DatabaseValidator.validate_job_data(invalid_data))
    
    def test_validate_confluence_publication_data_valid(self):
        """Test confluence publication data validation with valid data"""
        self.assertTrue(DatabaseValidator.validate_confluence_publication_data(self.valid_publication_data))
    
    def test_validate_confluence_publication_data_invalid(self):
        """Test confluence publication data validation with invalid data"""
        # Missing required fields
        required_fields = ['job_id', 'confluence_page_id', 'confluence_page_url',
                          'confluence_space_key', 'page_title']
        for field in required_fields:
            invalid_data = self.valid_publication_data.copy()
            del invalid_data[field]
            self.assertFalse(DatabaseValidator.validate_confluence_publication_data(invalid_data))
        
        # Invalid publication status
        invalid_data = self.valid_publication_data.copy()
        invalid_data['publication_status'] = 'invalid_status'
        self.assertFalse(DatabaseValidator.validate_confluence_publication_data(invalid_data))
        
        # Invalid retry count
        invalid_data = self.valid_publication_data.copy()
        invalid_data['retry_count'] = -1
        self.assertFalse(DatabaseValidator.validate_confluence_publication_data(invalid_data))
        
        invalid_data['retry_count'] = 'not_a_number'
        self.assertFalse(DatabaseValidator.validate_confluence_publication_data(invalid_data))
    
    def test_sanitize_user_data(self):
        """Test user data sanitization"""
        dirty_data = {
            'user_id': '  test_user_123  ',
            'email': '  test@example.com  ',
            'name': '  Test User  ',
            'extra_field': 'should_be_ignored'
        }
        
        sanitized = DatabaseValidator.sanitize_user_data(dirty_data)
        
        self.assertEqual(sanitized['user_id'], 'test_user_123')
        self.assertEqual(sanitized['email'], 'test@example.com')
        self.assertEqual(sanitized['name'], 'Test User')
        self.assertNotIn('extra_field', sanitized)
    
    def test_sanitize_job_data(self):
        """Test job data sanitization"""
        dirty_data = {
            'job_id': '  job_123  ',
            'user_id': '  user_123  ',
            'filename': '  test_meeting.mp3  ',
            'template': '  standard  ',
            'status': 'completed',
            'progress': '75',  # String that should be converted to int
            'metadata': {'key': 'value'}
        }
        
        sanitized = DatabaseValidator.sanitize_job_data(dirty_data)
        
        self.assertEqual(sanitized['job_id'], 'job_123')
        self.assertEqual(sanitized['user_id'], 'user_123')
        self.assertEqual(sanitized['filename'], 'test_meeting.mp3')
        self.assertEqual(sanitized['template'], 'standard')
        self.assertEqual(sanitized['progress'], 75)
        self.assertIsInstance(sanitized['metadata'], str)  # Should be JSON string
    
    def test_sanitize_confluence_publication_data(self):
        """Test confluence publication data sanitization"""
        dirty_data = {
            'job_id': '  job_123  ',
            'confluence_page_id': '  page_456  ',
            'confluence_page_url': '  https://test.atlassian.net/wiki/spaces/TEST/pages/456  ',
            'confluence_space_key': '  TEST  ',
            'page_title': '  20250902 - Test Meeting  ',
            'publication_status': PublicationStatus.PUBLISHED,
            'retry_count': '3'  # String that should be converted to int
        }
        
        sanitized = DatabaseValidator.sanitize_confluence_publication_data(dirty_data)
        
        self.assertEqual(sanitized['job_id'], 'job_123')
        self.assertEqual(sanitized['confluence_page_id'], 'page_456')
        self.assertEqual(sanitized['confluence_page_url'], 'https://test.atlassian.net/wiki/spaces/TEST/pages/456')
        self.assertEqual(sanitized['confluence_space_key'], 'TEST')
        self.assertEqual(sanitized['page_title'], '20250902 - Test Meeting')
        self.assertEqual(sanitized['retry_count'], 3)


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for database models with actual SQLite database"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
        
        # Create database schema
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Execute schema creation
        schema_sql = DatabaseSchema.get_create_tables_sql()
        for sql in schema_sql:
            self.conn.execute(sql)
        
        index_sql = DatabaseSchema.get_create_indexes_sql()
        for sql in index_sql:
            self.conn.execute(sql)
        
        self.conn.commit()
    
    def tearDown(self):
        """Clean up test database"""
        self.conn.close()
        os.unlink(self.db_path)
    
    def test_database_schema_creation(self):
        """Test that database schema is created correctly"""
        cursor = self.conn.cursor()
        
        # Check that all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('users', tables)
        self.assertIn('jobs', tables)
        self.assertIn('confluence_publications', tables)
        
        # Check that indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('idx_jobs_user_id', indexes)
        self.assertIn('idx_confluence_publications_job_id', indexes)
    
    def test_confluence_publications_table_structure(self):
        """Test confluence_publications table structure"""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(confluence_publications)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        expected_columns = {
            'id': 'INTEGER',
            'job_id': 'TEXT',
            'confluence_page_id': 'TEXT',
            'confluence_page_url': 'TEXT',
            'confluence_space_key': 'TEXT',
            'parent_page_id': 'TEXT',
            'page_title': 'TEXT',
            'publication_status': 'TEXT',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP',
            'error_message': 'TEXT',
            'retry_count': 'INTEGER',
            'last_retry_at': 'TIMESTAMP'
        }
        
        for col_name, col_type in expected_columns.items():
            self.assertIn(col_name, columns)
    
    def test_confluence_publications_constraints(self):
        """Test confluence_publications table constraints"""
        cursor = self.conn.cursor()
        
        # Test unique constraint on (job_id, confluence_page_id)
        cursor.execute("""
            INSERT INTO confluence_publications 
            (job_id, confluence_page_id, confluence_page_url, confluence_space_key, page_title)
            VALUES ('job1', 'page1', 'http://example.com/page1', 'TEST', 'Test Page 1')
        """)
        
        # This should fail due to unique constraint
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO confluence_publications
                (job_id, confluence_page_id, confluence_page_url, confluence_space_key, page_title)
                VALUES ('job1', 'page1', 'http://example.com/page1', 'TEST', 'Test Page 1 Duplicate')
            """)


if __name__ == '__main__':
    unittest.main()