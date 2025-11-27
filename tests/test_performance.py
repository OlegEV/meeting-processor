
#!/usr/bin/env python3
"""
Performance and load tests for Confluence integration
"""

import os
import sys
import time
import threading
import concurrent.futures
import statistics
import unittest
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from database.models import User, Job, ConfluencePublication, JobStatus, PublicationStatus
from confluence_client import ConfluenceServerClient, ConfluencePublicationService
from confluence_encryption import ConfluenceTokenManager
from tests.test_fixtures import (
    TestDataFactory, MockDataGenerator, PerformanceTestData,
    TestEnvironmentSetup, MockConfluenceClient
)


class PerformanceTestBase(unittest.TestCase):
    """Base class for performance tests"""
    
    def setUp(self):
        """Set up test environment"""
        db_config = {'path': ':memory:'}
        self.db_manager = DatabaseManager(db_config)
        
        # Performance tracking
        self.performance_metrics = {
            'operation_times': [],
            'memory_usage': [],
            'concurrent_operations': [],
            'error_rates': []
        }
        
        # Test configuration
        self.test_config = {
            'max_operation_time': 5.0,  # seconds
            'max_concurrent_users': 50,
            'bulk_operation_size': 1000,
            'stress_test_duration': 30  # seconds
        }
    
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
    
    def measure_operation_time(self, operation_func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure operation execution time"""
        start_time = time.time()
        try:
            result = operation_func(*args, **kwargs)
            execution_time = time.time() - start_time
            self.performance_metrics['operation_times'].append(execution_time)
            return result, execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            self.performance_metrics['operation_times'].append(execution_time)
            raise e
    
    def assert_performance_within_limits(self, execution_time: float, max_time: float = None):
        """Assert that operation completed within performance limits"""
        max_allowed = max_time or self.test_config['max_operation_time']
        self.assertLess(
            execution_time, 
            max_allowed,
            f"Operation took {execution_time:.3f}s, exceeding limit of {max_allowed}s"
        )
    
    def calculate_performance_stats(self, times: List[float]) -> Dict[str, float]:
        """Calculate performance statistics"""
        if not times:
            return {}
        
        return {
            'min': min(times),
            'max': max(times),
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
            'p95': sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0],
            'p99': sorted(times)[int(len(times) * 0.99)] if len(times) > 1 else times[0]
        }


class DatabasePerformanceTests(PerformanceTestBase):
    """Performance tests for database operations"""
    
    def test_bulk_user_creation_performance(self):
        """Test performance of bulk user creation"""
        print("\n=== Testing Bulk User Creation Performance ===")
        
        num_users = 1000
        users_data = [
            TestDataFactory.create_user_data(f'perf_user_{i}')
            for i in range(num_users)
        ]
        
        # Measure bulk creation time
        start_time = time.time()
        for user_data in users_data:
            self.db_manager.create_user(user_data)
        
        total_time = time.time() - start_time
        avg_time_per_user = total_time / num_users
        
        print(f"Created {num_users} users in {total_time:.3f}s")
        print(f"Average time per user: {avg_time_per_user:.6f}s")
        
        # Performance assertions
        self.assertLess(total_time, 10.0, "Bulk user creation took too long")
        self.assertLess(avg_time_per_user, 0.01, "Individual user creation too slow")
        
        # Verify data integrity
        all_users = self.db_manager.get_all_users()
        self.assertEqual(len(all_users), num_users)
    
    def test_bulk_job_creation_performance(self):
        """Test performance of bulk job creation"""
        print("\n=== Testing Bulk Job Creation Performance ===")
        
        # Create test user first
        user_data = TestDataFactory.create_user_data('perf_user')
        self.db_manager.create_user(user_data)
        
        num_jobs = 1000
        jobs_data = [
            TestDataFactory.create_job_data(f'perf_job_{i}', user_data['user_id'])
            for i in range(num_jobs)
        ]
        
        # Measure bulk creation time
        start_time = time.time()
        for job_data in jobs_data:
            self.db_manager.create_job(job_data)
        
        total_time = time.time() - start_time
        avg_time_per_job = total_time / num_jobs
        
        print(f"Created {num_jobs} jobs in {total_time:.3f}s")
        print(f"Average time per job: {avg_time_per_job:.6f}s")
        
        # Performance assertions
        self.assertLess(total_time, 15.0, "Bulk job creation took too long")
        self.assertLess(avg_time_per_job, 0.015, "Individual job creation too slow")
        
        # Verify data integrity
        user_jobs = self.db_manager.get_user_jobs(user_data['user_id'])
        self.assertEqual(len(user_jobs), num_jobs)
    
    def test_bulk_publication_creation_performance(self):
        """Test performance of bulk publication creation"""
        print("\n=== Testing Bulk Publication Creation Performance ===")
        
        # Create test user and jobs
        user_data = TestDataFactory.create_user_data('perf_user')
        self.db_manager.create_user(user_data)
        
        num_publications = 500
        publications_data = []
        
        for i in range(num_publications):
            job_data = TestDataFactory.create_job_data(f'perf_job_{i}', user_data['user_id'])
            self.db_manager.create_job(job_data)
            
            pub_data = TestDataFactory.create_confluence_publication_data(
                job_data['job_id'],
                confluence_page_id=f'perf_page_{i}'
            )
            publications_data.append(pub_data)
        
        # Measure bulk creation time
        start_time = time.time()
        for pub_data in publications_data:
            self.db_manager.create_confluence_publication(pub_data)
        
        total_time = time.time() - start_time
        avg_time_per_pub = total_time / num_publications
        
        print(f"Created {num_publications} publications in {total_time:.3f}s")
        print(f"Average time per publication: {avg_time_per_pub:.6f}s")
        
        # Performance assertions
        self.assertLess(total_time, 20.0, "Bulk publication creation took too long")
        self.assertLess(avg_time_per_pub, 0.04, "Individual publication creation too slow")
        
        # Verify data integrity
        all_publications = self.db_manager.get_all_confluence_publications()
        self.assertEqual(len(all_publications), num_publications)
    
    def test_complex_query_performance(self):
        """Test performance of complex database queries"""
        print("\n=== Testing Complex Query Performance ===")
        
        # Create test data
        test_data = TestEnvironmentSetup.create_test_database_with_data(
            self.db_manager, 
            num_users=50, 
            num_jobs_per_user=20,
            num_publications_per_job=1
        )
        
        # Test various query patterns
        query_tests = [
            ("get_all_users", lambda: self.db_manager.get_all_users()),
            ("get_all_jobs", lambda: self.db_manager.get_all_jobs()),
            ("get_all_publications", lambda: self.db_manager.get_all_confluence_publications()),
            ("get_user_jobs", lambda: self.db_manager.get_user_jobs(test_data['users'][0])),
            ("get_job_publications", lambda: self.db_manager.get_job_confluence_publications(test_data['jobs'][0]))
        ]
        
        for query_name, query_func in query_tests:
            result, execution_time = self.measure_operation_time(query_func)
            print(f"{query_name}: {execution_time:.6f}s, returned {len(result) if hasattr(result, '__len__') else 1} records")
            
            # Performance assertion
            self.assertLess(execution_time, 1.0, f"{query_name} query too slow")
    
    def test_database_transaction_performance(self):
        """Test performance of database transactions"""
        print("\n=== Testing Database Transaction Performance ===")
        
        num_operations = 100
        
        # Test transaction performance
        start_time = time.time()
        
        for i in range(num_operations):
            user_data = TestDataFactory.create_user_data(f'trans_user_{i}')
            job_data = TestDataFactory.create_job_data(f'trans_job_{i}', user_data['user_id'])
            
            # Simulate transaction-like operations
            self.db_manager.create_user(user_data)
            self.db_manager.create_job(job_data)
            self.db_manager.update_job_status(job_data['job_id'], JobStatus.COMPLETED, 100)
        
        total_time = time.time() - start_time
        avg_time_per_transaction = total_time / num_operations
        
        print(f"Completed {num_operations} transactions in {total_time:.3f}s")
        print(f"Average time per transaction: {avg_time_per_transaction:.6f}s")
        
        # Performance assertions
        self.assertLess(total_time, 5.0, "Transaction processing took too long")
        self.assertLess(avg_time_per_transaction, 0.05, "Individual transactions too slow")


class ConcurrencyTests(PerformanceTestBase):
    """Tests for concurrent operations"""
    
    def test_concurrent_user_creation(self):
        """Test concurrent user creation"""
        print("\n=== Testing Concurrent User Creation ===")
        
        num_threads = 10
        users_per_thread = 50
        
        def create_users_batch(thread_id: int) -> List[float]:
            """Create a batch of users and return timing data"""
            times = []
            for i in range(users_per_thread):
                user_data = TestDataFactory.create_user_data(f'concurrent_user_{thread_id}_{i}')
                
                start_time = time.time()
                try:
                    self.db_manager.create_user(user_data)
                    execution_time = time.time() - start_time
                    times.append(execution_time)
                except Exception as e:
                    print(f"Error in thread {thread_id}: {e}")
                    times.append(-1)  # Mark as error
            
            return times
        
        # Execute concurrent operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(create_users_batch, thread_id)
                for thread_id in range(num_threads)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        all_times = [time for batch in results for time in batch if time > 0]
        error_count = sum(1 for batch in results for time in batch if time < 0)
        
        print(f"Concurrent creation completed in {total_time:.3f}s")
        print(f"Total operations: {num_threads * users_per_thread}")
        print(f"Successful operations: {len(all_times)}")
        print(f"Failed operations: {error_count}")
        
        if all_times:
            stats = self.calculate_performance_stats(all_times)
            print(f"Performance stats: {stats}")
        
        # Assertions
        self.assertLess(error_count / (num_threads * users_per_thread), 0.05, "Too many errors in concurrent operations")
        self.assertLess(total_time, 30.0, "Concurrent operations took too long")
        
        # Verify data integrity
        all_users = self.db_manager.get_all_users()
        expected_users = num_threads * users_per_thread - error_count
        self.assertEqual(len(all_users), expected_users)
    
    def test_concurrent_job_processing(self):
        """Test concurrent job processing simulation"""
        print("\n=== Testing Concurrent Job Processing ===")
        
        # Create test users
        num_users = 5
        users = []
        for i in range(num_users):
            user_data = TestDataFactory.create_user_data(f'job_user_{i}')
            self.db_manager.create_user(user_data)
            users.append(user_data)
        
        num_jobs_per_user = 20
        
        def process_user_jobs(user_data: Dict[str, Any]) -> List[float]:
            """Process jobs for a single user"""
            times = []
            
            for i in range(num_jobs_per_user):
                job_data = TestDataFactory.create_job_data(
                    f'concurrent_job_{user_data["user_id"]}_{i}',
                    user_data['user_id'],
                    status=JobStatus.PROCESSING
                )
                
                start_time = time.time()
                try:
                    # Simulate job processing workflow
                    self.db_manager.create_job(job_data)
                    
                    # Simulate processing steps
                    self.db_manager.update_job_status(job_data['job_id'], JobStatus.PROCESSING, 25)
                    self.db_manager.update_job_status(job_data['job_id'], JobStatus.PROCESSING, 50)
                    self.db_manager.update_job_status(job_data['job_id'], JobStatus.PROCESSING, 75)
                    self.db_manager.update_job_status(job_data['job_id'], JobStatus.COMPLETED, 100)
                    
                    execution_time = time.time() - start_time
                    times.append(execution_time)
                except Exception as e:
                    print(f"Error processing job for user {user_data['user_id']}: {e}")
                    times.append(-1)
            
            return times
        
        # Execute concurrent job processing
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [
                executor.submit(process_user_jobs, user_data)
                for user_data in users
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        all_times = [time for batch in results for time in batch if time > 0]
        error_count = sum(1 for batch in results for time in batch if time < 0)
        
        print(f"Concurrent job processing completed in {total_time:.3f}s")
        print(f"Total jobs: {num_users * num_jobs_per_user}")
        print(f"Successful jobs: {len(all_times)}")
        print(f"Failed jobs: {error_count}")
        
        if all_times:
            stats = self.calculate_performance_stats(all_times)
            print(f"Performance stats: {stats}")
        
        # Assertions
        self.assertLess(error_count / (num_users * num_jobs_per_user), 0.05, "Too many job processing errors")
        self.assertLess(total_time, 60.0, "Concurrent job processing took too long")
    
    def test_concurrent_confluence_publication(self):
        """Test concurrent Confluence publication simulation"""
        print("\n=== Testing Concurrent Confluence Publication ===")
        
        # Create test data
        num_users = 3
        jobs_per_user = 10
        
        test_jobs = []
        for i in range(num_users):
            user_data = TestDataFactory.create_user_data(f'pub_user_{i}')
            self.db_manager.create_user(user_data)
            
            for j in range(jobs_per_user):
                job_data = TestDataFactory.create_job_data(
                    f'pub_job_{i}_{j}',
                    user_data['user_id'],
                    status=JobStatus.COMPLETED
                )
                self.db_manager.create_job(job_data)
                test_jobs.append(job_data)
        
        def simulate_confluence_publication(job_data: Dict[str, Any]) -> float:
            """Simulate Confluence publication for a job"""
            start_time = time.time()
            
            try:
                # Simulate publication workflow
                pub_data = TestDataFactory.create_confluence_publication_data(
                    job_data['job_id'],
                    publication_status=PublicationStatus.PENDING
                )
                
                # Create publication record
                publication = self.db_manager.create_confluence_publication(pub_data)
                
                # Simulate API call delay
                time.sleep(0.1)  # Simulate network latency
                
                # Update to published status
                self.db_manager.update_confluence_publication_status(
                    publication['id'],
                    PublicationStatus.PUBLISHED,
                    f'https://test.atlassian.net/wiki/spaces/TEST/pages/{publication["id"]}'
                )
                
                return time.time() - start_time
                
            except Exception as e:
                print(f"Error publishing job {job_data['job_id']}: {e}")
                return -1
        
        # Execute concurrent publications
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(simulate_confluence_publication, job_data)
                for job_data in test_jobs
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_times = [time for time in results if time > 0]
        error_count = sum(1 for time in results if time < 0)
        
        print(f"Concurrent publication completed in {total_time:.3f}s")
        print(f"Total publications: {len(test_jobs)}")
        print(f"Successful publications: {len(successful_times)}")
        print(f"Failed publications: {error_count}")
        
        if successful_times:
            stats = self.calculate_performance_stats(successful_times)
            print(f"Performance stats: {stats}")
        
        # Assertions
        self.assertLess(error_count / len(test_jobs), 0.1, "Too many publication errors")
        self.assertLess(total_time, 45.0, "Concurrent publication took too long")
        
        # Verify data integrity
        all_publications = self.db_manager.get_all_confluence_publications()
        self.assertEqual(len(all_publications), len(test_jobs) - error_count)


class ConfluenceClientPerformanceTests(PerformanceTestBase):
    """Performance tests for Confluence client operations"""
    
    def setUp(self):
        """Set up Confluence client tests"""
        super().setUp()
        self.mock_client = MockConfluenceClient()
        self.confluence_config = TestDataFactory.create_confluence_config()
    
    @patch('confluence_client.ConfluenceServerClient')
    def test_confluence_api_response_times(self, mock_client_class):
        """Test Confluence API response times"""
        print("\n=== Testing Confluence API Response Times ===")
        
        # Configure mock
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        # Mock API responses with simulated delays
        def mock_create_page(*args, **kwargs):
            time.sleep(0.2)  # Simulate API latency
            return MockDataGenerator.create_confluence_api_responses()['create_page_success']
        
        def mock_get_page_info(*args, **kwargs):
            time.sleep(0.1)  # Simulate API latency
            return MockDataGenerator.create_confluence_api_responses()['get_page_info']
        
        def mock_search_pages(*args, **kwargs):
            time.sleep(0.15)  # Simulate API latency
            return MockDataGenerator.create_confluence_api_responses()['search_pages']['results']
        
        mock_client_instance.create_page = mock_create_page
        mock_client_instance.get_page_info = mock_get_page_info
        mock_client_instance.search_pages = mock_search_pages
        mock_client_instance.test_connection.return_value = True
        
        # Test different API operations
        operations = [
            ("create_page", lambda: mock_client_instance.create_page(
                "Test Page", 
                MockDataGenerator.create_meeting_protocol_content()
            )),
            ("get_page_info", lambda: mock_client_instance.get_page_info("123456")),
            ("search_pages", lambda: mock_client_instance.search_pages("test query")),
            ("test_connection", lambda: mock_client_instance.test_connection())
        ]
        
        for operation_name, operation_func in operations:
            times = []
            
            # Run operation multiple times
            for _ in range(10):
                result, execution_time = self.measure_operation_time(operation_func)
                times.append(execution_time)
            
            stats = self.calculate_performance_stats(times)
            print(f"{operation_name}: {stats}")
            
            # Performance assertions
            if operation_name == "create_page":
                self.assertLess(stats['mean'], 0.5, f"{operation_name} too slow")
            else:
                self.assertLess(stats['mean'], 0.3, f"{operation_name} too slow")
    
    def test_large_content_publication_performance(self):
        """Test performance with large content"""
        print("\n=== Testing Large Content Publication Performance ===")
        
        # Test different content sizes
        content_sizes = [10, 50, 100, 500]  # KB
        
        for size_kb in content_sizes:
            large_content = PerformanceTestData.generate_large_content(size_kb)
            
            # Measure content processing time
            start_time = time.time()
            
            # Simulate content processing operations
            content_length = len(large_content)
            content_lines = large_content.count('\n')
            content_words = len(large_content.split())
            
            processing_time = time.time() - start_time
            
            print(f"Content size: {size_kb}KB")
            print(f"  Characters: {content_length:,}")
            print(f"  Lines: {content_lines:,}")
            print(f"  Words: {content_words:,}")
            print(f"  Processing time: {processing_time:.6f}s")
            
            # Performance assertions
            self.assertLess(processing_time, 1.0, f"Content processing too slow for {size_kb}KB")
            self.assertLess(processing_time / content_length, 0.000001, "Processing per character too slow")
    
    def test_encryption_performance(self):
        """Test encryption/decryption performance"""
        print("\n=== Testing Encryption Performance ===")
        
        # Test different token sizes
        token_sizes = [32, 128, 512, 1024]  # characters
        
        for size in token_sizes:
            test_token = "x" * size
            
            # Measure encryption performance
            encryption_times = []
            decryption_times = []
            
            for _ in range(100):
                # Encryption
                start_time = time.time()
                encrypted = ConfluenceTokenManager.encrypt_token(test_token)
                encryption_time = time.time() - start_time
                encryption_times.append(encryption_time)
                
                # Decryption
                start_time = time.time()
                decrypted = ConfluenceTokenManager.decrypt_token(encrypted)
                decryption_time = time.time() - start_time
                decryption_times.append(decryption_time)
                
                # Verify correctness
                self.assertEqual(decrypted, test_token)
            
            enc_stats = self.calculate_performance_stats(encryption_times)
            dec_stats = self.calculate_performance_stats(decryption_times)
            
            print(f"Token size: {size} characters")
            print(f"  Encryption: {enc_stats}")
            print(f"  Decryption: {dec_stats}")
            
            # Performance assertions
            self.assertLess(enc_stats['mean'], 0.01, f"Encryption too slow for {size} chars")
            self.assertLess(dec_stats['mean'], 0.01, f"Decryption too slow for {size} chars")


class StressTests(PerformanceTestBase):
    """Stress tests for system limits"""
    
    def test_memory_usage_under_load(self):
        """Test memory usage under heavy load"""
        print("\n=== Testing Memory Usage Under Load ===")
        
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Create large dataset
        large_dataset = PerformanceTestData.generate_bulk_test_data(
            num_users=200,
            num_jobs_per_user=100
        )
        
        # Process data in batches
        batch_size = 50
        memory_readings = []
        
        for i in range(0, len(large_dataset['users']), batch_size):
            batch_users = large_dataset['users'][i:i+batch_size]
            
            # Process batch
            for user_data in batch_users:
                self.db_manager.create_user(user_data)
            
            # Measure memory
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_readings.append(current_memory)
            
            # Force garbage collection
            gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        max_memory = max(memory_readings)
        memory_growth = final_memory - initial_memory
        
        print(f"Final memory usage: {final_memory:.2f} MB")
        print(f"Maximum memory usage: {max_memory:.2f} MB")
        print(f"Memory growth: {memory_growth:.2f} MB")
        
        # Memory assertions
        self.assertLess(memory_growth, 500, "Excessive memory growth")  # 500MB limit
        self.assertLess(max_memory, 1000, "Peak memory usage too high")  # 1GB limit
    
    def test_database_connection_limits(self):
        """Test database connection handling under stress"""
        print("\n=== Testing Database Connection Limits ===")
        
        num_concurrent_connections = 20
        operations_per_connection = 50
        
        def database_stress_worker(worker_id: int) -> Dict[str, Any]:
            """Worker function for database stress testing"""
            # Create separate database manager for this worker
            worker_db = DatabaseManager(':memory:')
            worker_db.init_database()
            
            results = {
                'worker_id': worker_id,
                'operations_completed': 0,
                'errors': 0,
                'total_time': 0
            }
            
            start_time = time.time()
            
            try:
                for i in range(operations_per_connection):
                    try:
                        # Mix of different operations
                        if i % 4 == 0:
                            user_data = TestDataFactory.create_user_data(f'stress_user_{worker_id}_{i}')
                            worker_db.create_user(user_data)
                        elif i % 4 == 1:
                            job_data = TestDataFactory.create_job_data(f'stress_job_{worker_id}_{i}', f'stress_user_{worker_id}_0')
                            worker_db.create_job(job_data)
                        elif i % 4 == 2:
                            users = worker_db.get_all_users()
                        else:
                            jobs = worker_db.get_all_jobs()
                        
                        results['operations_completed'] += 1
                        
                    except Exception as e:
                        results['errors'] += 1
                        print(f"Worker {worker_id} error: {e}")
                
            finally:
                results['total_time'] = time.time() - start_time
                worker_db.close()
            
            return results
        
        # Execute stress test
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_connections) as executor:
            futures = [
                executor.submit(database_stress_worker, worker_id)
                for worker_id in range(num_concurrent_connections)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        total_operations = sum(r['operations_completed'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        error_rate = total_errors / (total_operations + total_errors) if (total_operations + total_errors) > 0 else 0
        
        print(f"Stress test completed in {total_time:.3f}s")
        print(f"Total operations: {total_operations}")
        print(f"Total errors: {total_errors}")
        print(f"Error rate: {error_rate:.3%}")
        print(f"Operations per second: {total_operations / total_time:.2f}")
        
        