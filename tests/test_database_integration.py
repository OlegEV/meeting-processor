#!/usr/bin/env python3
"""
Integration tests for database operations with Confluence functionality
"""

import unittest
import tempfile
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from database.models import (
    User, Job, ConfluencePublication, PublicationStatus, JobStatus,
    DatabaseSchema, DatabaseValidator
)


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
        
        # Create database configuration
        self.db_config = {
            'path': self.db_path,
            'timeout': 30,
            'check_same_thread': False
        }
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.db_config)
        
        # Create test users
        self.test_users = [
            {
                'user_id': 'user_1',
                'email': 'user1@example.com',
                'name': 'User One',
                'full_name': 'User One Full'
            },
            {
                'user_id': 'user_2',
                'email': 'user2@example.com',
                'name': 'User Two',
                'full_name': 'User Two Full'
            }
        ]
        
        # Create test users in database
        for user_data in self.test_users:
            self.db_manager.create_user(user_data)
    
    def tearDown(self):
        """Clean up test database"""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass
    
    def test_database_initialization(self):
        """Test database initialization and schema creation"""
        # Verify tables exist
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['users', 'jobs', 'confluence_publications']
        for table in expected_tables:
            self.assertIn(table, tables)
    
    def test_user_job_relationship(self):
        """Test relationship between users and jobs"""
        user_id = 'user_1'
        
        # Create multiple jobs for user
        job_data_list = [
            {
                'job_id': 'job_1',
                'user_id': user_id,
                'filename': 'meeting1.mp3',
                'template': 'standard',
                'status': 'completed',
                'progress': 100
            },
            {
                'job_id': 'job_2',
                'user_id': user_id,
                'filename': 'meeting2.mp3',
                'template': 'business',
                'status': 'processing',
                'progress': 50
            }
        ]
        
        for job_data in job_data_list:
            self.db_manager.create_job(job_data)
        
        # Get user jobs
        user_jobs = self.db_manager.get_user_jobs(user_id)
        
        self.assertEqual(len(user_jobs), 2)
        job_ids = [job['job_id'] for job in user_jobs]
        self.assertIn('job_1', job_ids)
        self.assertIn('job_2', job_ids)
    
    def test_job_confluence_publication_relationship(self):
        """Test relationship between jobs and Confluence publications"""
        user_id = 'user_1'
        job_id = 'job_with_publications'
        
        # Create job
        job_data = {
            'job_id': job_id,
            'user_id': user_id,
            'filename': 'meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        self.db_manager.create_job(job_data)
        
        # Create multiple publications for the job
        publication_data_list = [
            {
                'job_id': job_id,
                'confluence_page_id': 'page_1',
                'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/1',
                'confluence_space_key': 'TEST',
                'page_title': '20250902 - Meeting 1',
                'publication_status': PublicationStatus.PUBLISHED
            },
            {
                'job_id': job_id,
                'confluence_page_id': 'page_2',
                'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/2',
                'confluence_space_key': 'TEST',
                'page_title': '20250902 - Meeting 1 (Retry)',
                'publication_status': PublicationStatus.FAILED,
                'error_message': 'Network error'
            }
        ]
        
        publication_ids = []
        for pub_data in publication_data_list:
            publication = self.db_manager.create_confluence_publication(pub_data)
            publication_ids.append(publication['id'])
        
        # Get publications for job
        job_publications = self.db_manager.get_confluence_publications_by_job_id(job_id)
        
        self.assertEqual(len(job_publications), 2)
        
        # Verify publication details
        published_pub = next(p for p in job_publications if p['publication_status'] == PublicationStatus.PUBLISHED)
        failed_pub = next(p for p in job_publications if p['publication_status'] == PublicationStatus.FAILED)
        
        self.assertEqual(published_pub['confluence_page_id'], 'page_1')
        self.assertEqual(failed_pub['confluence_page_id'], 'page_2')
        self.assertEqual(failed_pub['error_message'], 'Network error')
    
    def test_cascade_delete_user_jobs(self):
        """Test cascade deletion of jobs when user is deleted"""
        user_id = 'user_to_delete'
        
        # Create user
        user_data = {
            'user_id': user_id,
            'email': 'delete@example.com',
            'name': 'Delete User'
        }
        self.db_manager.create_user(user_data)
        
        # Create jobs for user
        job_ids = ['job_delete_1', 'job_delete_2']
        for job_id in job_ids:
            job_data = {
                'job_id': job_id,
                'user_id': user_id,
                'filename': f'{job_id}.mp3',
                'template': 'standard',
                'status': 'completed',
                'progress': 100
            }
            self.db_manager.create_job(job_data)
        
        # Verify jobs exist
        user_jobs = self.db_manager.get_user_jobs(user_id)
        self.assertEqual(len(user_jobs), 2)
        
        # Delete user
        self.db_manager.delete_user(user_id)
        
        # Verify jobs are also deleted (cascade)
        for job_id in job_ids:
            job = self.db_manager.get_job_by_id(job_id)
            self.assertIsNone(job)
    
    def test_cascade_delete_job_publications(self):
        """Test cascade deletion of publications when job is deleted"""
        user_id = 'user_1'
        job_id = 'job_to_delete'
        
        # Create job
        job_data = {
            'job_id': job_id,
            'user_id': user_id,
            'filename': 'meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        self.db_manager.create_job(job_data)
        
        # Create publications for job
        publication_data = {
            'job_id': job_id,
            'confluence_page_id': 'page_to_delete',
            'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/delete',
            'confluence_space_key': 'TEST',
            'page_title': '20250902 - Meeting to Delete',
            'publication_status': PublicationStatus.PUBLISHED
        }
        publication = self.db_manager.create_confluence_publication(publication_data)
        publication_id = publication['id']
        
        # Verify publication exists
        pub = self.db_manager.get_confluence_publication_by_id(publication_id)
        self.assertIsNotNone(pub)
        
        # Delete job
        self.db_manager.delete_job(job_id)
        
        # Verify publication is also deleted (cascade)
        pub = self.db_manager.get_confluence_publication_by_id(publication_id)
        self.assertIsNone(pub)
    
    def test_confluence_publication_statistics(self):
        """Test Confluence publication statistics calculation"""
        user_id = 'user_1'
        
        # Create jobs and publications with different statuses
        test_data = [
            ('job_stat_1', PublicationStatus.PUBLISHED, None),
            ('job_stat_2', PublicationStatus.PUBLISHED, None),
            ('job_stat_3', PublicationStatus.FAILED, 'Auth error'),
            ('job_stat_4', PublicationStatus.RETRYING, 'Network timeout'),
            ('job_stat_5', PublicationStatus.PENDING, None)
        ]
        
        for job_id, status, error in test_data:
            # Create job
            job_data = {
                'job_id': job_id,
                'user_id': user_id,
                'filename': f'{job_id}.mp3',
                'template': 'standard',
                'status': 'completed',
                'progress': 100
            }
            self.db_manager.create_job(job_data)
            
            # Create publication
            pub_data = {
                'job_id': job_id,
                'confluence_page_id': f'page_{job_id}',
                'confluence_page_url': f'https://test.atlassian.net/wiki/spaces/TEST/pages/{job_id}',
                'confluence_space_key': 'TEST',
                'page_title': f'20250902 - {job_id}',
                'publication_status': status,
                'error_message': error
            }
            self.db_manager.create_confluence_publication(pub_data)
        
        # Get statistics
        stats = self.db_manager.get_confluence_publications_statistics()
        
        # Verify overall statistics
        self.assertEqual(stats['overall']['total_publications'], 5)
        self.assertEqual(stats['overall']['published_count'], 2)
        self.assertEqual(stats['overall']['failed_count'], 1)
        self.assertEqual(stats['overall']['pending_count'], 1)
        self.assertEqual(stats['overall']['retrying_count'], 1)
        
        # Verify space statistics
        self.assertEqual(len(stats['by_space']), 1)
        space_stats = stats['by_space'][0]
        self.assertEqual(space_stats['confluence_space_key'], 'TEST')
        self.assertEqual(space_stats['total_publications'], 5)
        self.assertEqual(space_stats['published_count'], 2)
    
    def test_publication_retry_functionality(self):
        """Test publication retry functionality"""
        user_id = 'user_1'
        job_id = 'job_retry_test'
        
        # Create job
        job_data = {
            'job_id': job_id,
            'user_id': user_id,
            'filename': 'retry_meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        self.db_manager.create_job(job_data)
        
        # Create failed publication
        pub_data = {
            'job_id': job_id,
            'confluence_page_id': 'page_retry',
            'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TEST/pages/retry',
            'confluence_space_key': 'TEST',
            'page_title': '20250902 - Retry Test',
            'publication_status': PublicationStatus.FAILED,
            'error_message': 'Initial failure',
            'retry_count': 0
        }
        publication = self.db_manager.create_confluence_publication(pub_data)
        publication_id = publication['id']
        
        # Simulate retry attempts
        for retry_num in range(1, 4):
            update_data = {
                'publication_status': PublicationStatus.RETRYING,
                'retry_count': retry_num,
                'last_retry_at': datetime.utcnow().isoformat(),
                'error_message': f'Retry attempt {retry_num} failed'
            }
            self.db_manager.update_confluence_publication(publication_id, update_data)
            
            # Verify update
            pub = self.db_manager.get_confluence_publication_by_id(publication_id)
            self.assertEqual(pub['retry_count'], retry_num)
            self.assertEqual(pub['publication_status'], PublicationStatus.RETRYING)
        
        # Final successful retry
        final_update = {
            'publication_status': PublicationStatus.PUBLISHED,
            'error_message': None
        }
        self.db_manager.update_confluence_publication(publication_id, final_update)
        
        # Verify final state
        pub = self.db_manager.get_confluence_publication_by_id(publication_id)
        self.assertEqual(pub['publication_status'], PublicationStatus.PUBLISHED)
        self.assertEqual(pub['retry_count'], 3)
        self.assertIsNone(pub['error_message'])
    
    def test_publication_search_and_filtering(self):
        """Test publication search and filtering functionality"""
        user_id = 'user_1'
        
        # Create publications with different statuses and dates
        base_time = datetime.utcnow()
        test_publications = [
            {
                'job_id': 'job_search_1',
                'status': PublicationStatus.PUBLISHED,
                'space': 'SPACE1',
                'created_offset_days': -5
            },
            {
                'job_id': 'job_search_2',
                'status': PublicationStatus.FAILED,
                'space': 'SPACE1',
                'created_offset_days': -3
            },
            {
                'job_id': 'job_search_3',
                'status': PublicationStatus.PUBLISHED,
                'space': 'SPACE2',
                'created_offset_days': -1
            },
            {
                'job_id': 'job_search_4',
                'status': PublicationStatus.PENDING,
                'space': 'SPACE1',
                'created_offset_days': 0
            }
        ]
        
        for i, pub_info in enumerate(test_publications):
            # Create job
            job_data = {
                'job_id': pub_info['job_id'],
                'user_id': user_id,
                'filename': f'search_{i}.mp3',
                'template': 'standard',
                'status': 'completed',
                'progress': 100
            }
            self.db_manager.create_job(job_data)
            
            # Create publication
            pub_data = {
                'job_id': pub_info['job_id'],
                'confluence_page_id': f'page_search_{i}',
                'confluence_page_url': f'https://test.atlassian.net/wiki/spaces/{pub_info["space"]}/pages/{i}',
                'confluence_space_key': pub_info['space'],
                'page_title': f'20250902 - Search Test {i}',
                'publication_status': pub_info['status']
            }
            publication = self.db_manager.create_confluence_publication(pub_data)
            
            # Update created_at to simulate different creation times
            if pub_info['created_offset_days'] != 0:
                created_at = base_time + timedelta(days=pub_info['created_offset_days'])
                with self.db_manager._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE confluence_publications SET created_at = ? WHERE id = ?",
                        (created_at.isoformat(), publication['id'])
                    )
                    conn.commit()
        
        # Test filtering by status
        published_pubs = self.db_manager.get_confluence_publications_by_status(PublicationStatus.PUBLISHED)
        self.assertEqual(len(published_pubs), 2)
        
        failed_pubs = self.db_manager.get_confluence_publications_by_status(PublicationStatus.FAILED)
        self.assertEqual(len(failed_pubs), 1)
        
        # Test filtering with limit
        limited_pubs = self.db_manager.get_confluence_publications_by_status(
            PublicationStatus.PUBLISHED, limit=1
        )
        self.assertEqual(len(limited_pubs), 1)
    
    def test_database_performance_with_large_dataset(self):
        """Test database performance with larger dataset"""
        user_id = 'user_1'
        
        # Create multiple jobs and publications
        num_jobs = 50
        jobs_created = []
        publications_created = []
        
        # Batch create jobs
        for i in range(num_jobs):
            job_data = {
                'job_id': f'perf_job_{i}',
                'user_id': user_id,
                'filename': f'performance_test_{i}.mp3',
                'template': 'standard',
                'status': 'completed' if i % 2 == 0 else 'processing',
                'progress': 100 if i % 2 == 0 else 50
            }
            self.db_manager.create_job(job_data)
            jobs_created.append(job_data['job_id'])
            
            # Create publications for completed jobs
            if i % 2 == 0:
                pub_data = {
                    'job_id': job_data['job_id'],
                    'confluence_page_id': f'perf_page_{i}',
                    'confluence_page_url': f'https://test.atlassian.net/wiki/spaces/PERF/pages/{i}',
                    'confluence_space_key': 'PERF',
                    'page_title': f'20250902 - Performance Test {i}',
                    'publication_status': PublicationStatus.PUBLISHED if i % 4 == 0 else PublicationStatus.FAILED
                }
                publication = self.db_manager.create_confluence_publication(pub_data)
                publications_created.append(publication['id'])
        
        # Test query performance
        import time
        
        # Test user jobs query
        start_time = time.time()
        user_jobs = self.db_manager.get_user_jobs(user_id)
        jobs_query_time = time.time() - start_time
        
        self.assertEqual(len(user_jobs), num_jobs)
        self.assertLess(jobs_query_time, 1.0)  # Should complete in less than 1 second
        
        # Test publications statistics query
        start_time = time.time()
        stats = self.db_manager.get_confluence_publications_statistics()
        stats_query_time = time.time() - start_time
        
        self.assertLess(stats_query_time, 1.0)  # Should complete in less than 1 second
        self.assertEqual(stats['overall']['total_publications'], len(publications_created))
    
    def test_concurrent_database_access(self):
        """Test concurrent database access"""
        import threading
        import time
        
        user_id = 'user_1'
        results = []
        errors = []
        
        def create_job_and_publication(thread_id):
            try:
                job_id = f'concurrent_job_{thread_id}'
                
                # Create job
                job_data = {
                    'job_id': job_id,
                    'user_id': user_id,
                    'filename': f'concurrent_{thread_id}.mp3',
                    'template': 'standard',
                    'status': 'completed',
                    'progress': 100
                }
                self.db_manager.create_job(job_data)
                
                # Create publication
                pub_data = {
                    'job_id': job_id,
                    'confluence_page_id': f'concurrent_page_{thread_id}',
                    'confluence_page_url': f'https://test.atlassian.net/wiki/spaces/CONC/pages/{thread_id}',
                    'confluence_space_key': 'CONC',
                    'page_title': f'20250902 - Concurrent Test {thread_id}',
                    'publication_status': PublicationStatus.PUBLISHED
                }
                publication = self.db_manager.create_confluence_publication(pub_data)
                
                results.append((thread_id, job_id, publication['id']))
                
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create multiple threads
        threads = []
        num_threads = 10
        
        for i in range(num_threads):
            thread = threading.Thread(target=create_job_and_publication, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), num_threads)
        
        # Verify all jobs and publications were created
        user_jobs = self.db_manager.get_user_jobs(user_id)
        concurrent_jobs = [job for job in user_jobs if job['job_id'].startswith('concurrent_job_')]
        self.assertEqual(len(concurrent_jobs), num_threads)
    
    def test_database_backup_and_restore(self):
        """Test database backup and restore functionality"""
        user_id = 'user_1'
        
        # Create test data
        job_data = {
            'job_id': 'backup_test_job',
            'user_id': user_id,
            'filename': 'backup_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        self.db_manager.create_job(job_data)
        
        pub_data = {
            'job_id': 'backup_test_job',
            'confluence_page_id': 'backup_page',
            'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/BACKUP/pages/1',
            'confluence_space_key': 'BACKUP',
            'page_title': '20250902 - Backup Test',
            'publication_status': PublicationStatus.PUBLISHED
        }
        self.db_manager.create_confluence_publication(pub_data)
        
        # Create backup
        backup_path = tempfile.mktemp(suffix='.db')
        try:
            # Simple backup using SQLite backup
            with self.db_manager._get_connection() as source_conn:
                with sqlite3.connect(backup_path) as backup_conn:
                    source_conn.backup(backup_conn)
            
            # Verify backup file exists and has data
            self.assertTrue(os.path.exists(backup_path))
            
            # Verify backup contains our data
            with sqlite3.connect(backup_path) as backup_conn:
                backup_conn.row_factory = sqlite3.Row
                cursor = backup_conn.cursor()
                
                # Check job exists
                cursor.execute("SELECT * FROM jobs WHERE job_id = ?", ('backup_test_job',))
                job_row = cursor.fetchone()
                self.assertIsNotNone(job_row)
                self.assertEqual(job_row['filename'], 'backup_test.mp3')
                
                # Check publication exists
                cursor.execute("SELECT * FROM confluence_publications WHERE job_id = ?", ('backup_test_job',))
                pub_row = cursor.fetchone()
                self.assertIsNotNone(pub_row)
                self.assertEqual(pub_row['confluence_page_id'], 'backup_page')
        
        finally:
            # Clean up backup file
            try:
                os.unlink(backup_path)
            except FileNotFoundError:
                pass


class TestDatabaseMigrations(unittest.TestCase):
    """Test database migration functionality"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
    
    def tearDown(self):
        """Clean up test database"""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass
    
    def test_migration_execution(self):
        """Test execution of database migrations"""
        # Create connection and execute migrations manually
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Execute migration 1 (initial schema)
            migration_1_sql = DatabaseSchema.get_migration_sql(1)
            for sql in migration_1_sql:
                conn.execute(sql)
            conn.commit()
            
            # Verify tables exist
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('users', tables)
            self.assertIn('jobs', tables)
            
            # Execute migration 2 (indexes)
            migration_2_sql = DatabaseSchema.get_migration_sql(2)
            for sql in migration_2_sql:
                conn.execute(sql)
            conn.commit()
            
            # Verify indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('idx_jobs_user_id', indexes)
            self.assertIn('idx_jobs_status', indexes)
            
            # Execute migration 3 (confluence integration)
            migration_3_sql = DatabaseSchema.get_migration_sql(3)
            for sql in migration_3_sql:
                conn.execute(sql)
            conn.commit()
            
            # Verify confluence_publications table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('confluence_publications', tables)
            
            # Verify confluence indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('idx_confluence_publications_job_id', indexes)
            self.assertIn('idx_confluence_publications_status', indexes)
            
            # Verify trigger exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
            triggers = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('update_confluence_publications_updated_at', triggers)
        
        finally:
            conn.close()
    
    def test_confluence_publications_trigger(self):
        """Test the updated_at trigger for confluence_publications"""
        # Initialize database with all migrations
        db_config = {
            'path': self.db_path,
            'timeout': 30,
            'check_same_thread': False
        }
        db_manager = DatabaseManager(db_config)
        
        # Create test user and job
        user_data = {
            'user_id': 'trigger_test_user',
            'email': 'trigger@example.com',
            'name': 'Trigger Test User'
        }
        db_manager.create_user(user_data)
        
        job_data = {
            'job_id': 'trigger_test_job',
            'user_id': 'trigger_test_user',
            'filename': 'trigger_test.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        db_manager.create_job(job_data)
        
        # Create publication
        pub_data = {
            'job_id': 'trigger_test_job',
            'confluence_page_id': 'trigger_page',
            'confluence_page_url': 'https://test.atlassian.net/wiki/spaces/TRIGGER/pages/1',
            'confluence_space_key': 'TRIGGER',
            'page_title': '20250902 - Trigger Test',
            'publication_status': PublicationStatus.PUBLISHED
        }
        publication = db_manager.create_confluence_publication(pub_data)
        publication_id = publication['id']
        
        # Get initial timestamps
        initial_pub = db_manager.get_confluence_publication_by_id(publication_id)
        initial_created_at = initial_pub['created_at']
        initial_updated_at = initial_pub['updated_at']
        
        # Wait a moment to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        # Update publication
        update_data = {
            'publication_status': PublicationStatus.FAILED,
            'error_message': 'Test error'
        }
        db_manager.update_confluence_publication(publication_id, update_data)
        
        # Get updated timestamps
        updated_pub = db_manager.get_confluence_publication_by_id(publication_id)
        updated_created_at = updated_pub['created_at']
        updated_updated_at = updated_pub['updated_at']
        
        # Verify trigger worked
        self.assertEqual(initial_created_at, updated_created_at)  # created_at should not change
        self.assertNotEqual(initial_updated_at, updated_updated_at)  # updated_at should change
        self.assertEqual(updated_pub['error_message'], 'Test error')


if __name__ == '__main__':
    unittest.main()