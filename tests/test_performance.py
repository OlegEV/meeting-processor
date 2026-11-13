#!/usr/bin/env python3
"""
Fixed performance tests for Confluence integration
"""

import os
import sys
import time
import unittest
import tempfile
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from tests.test_fixtures import TestDataFactory


class DatabasePerformanceTests(unittest.TestCase):
    """Performance tests for database operations"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        db_config = {'path': self.temp_db.name}
        self.db_manager = DatabaseManager(db_config)
        
        # Performance tracking
        self.performance_metrics = {
            'operation_times': [],
            'memory_usage': [],
            'concurrent_operations': [],
            'error_rates': []
        }
    
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        
        # Clean up temp file
        try:
            os.unlink(self.temp_db.name)
        except (FileNotFoundError, PermissionError):
            pass
    
    def test_bulk_user_creation_performance(self):
        """Test performance of bulk user creation"""
        print("\n=== Testing Bulk User Creation Performance ===")
        
        num_users = 100  # Reduced for faster testing
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
        self.assertLess(total_time, 5.0, "Bulk user creation took too long")
        self.assertLess(avg_time_per_user, 0.05, "Individual user creation too slow")
        
        # Verify data integrity
        all_users = self.db_manager.get_all_users()
        self.assertEqual(len(all_users), num_users)
    
    def test_bulk_job_creation_performance(self):
        """Test performance of bulk job creation"""
        print("\n=== Testing Bulk Job Creation Performance ===")
        
        # Create test user first
        user_data = TestDataFactory.create_user_data('perf_user')
        self.db_manager.create_user(user_data)
        
        num_jobs = 100  # Reduced for faster testing
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
        self.assertLess(total_time, 5.0, "Bulk job creation took too long")
        self.assertLess(avg_time_per_job, 0.05, "Individual job creation too slow")
        
        # Verify data integrity
        user_jobs = self.db_manager.get_user_jobs(user_data['user_id'])
        self.assertEqual(len(user_jobs), num_jobs)
    
    def test_complex_query_performance(self):
        """Test performance of complex database queries"""
        print("\n=== Testing Complex Query Performance ===")
        
        # Create test data
        num_users = 10
        num_jobs_per_user = 10
        
        for i in range(num_users):
            user_data = TestDataFactory.create_user_data(f'query_user_{i}')
            self.db_manager.create_user(user_data)
            
            for j in range(num_jobs_per_user):
                job_data = TestDataFactory.create_job_data(
                    f'query_job_{i}_{j}', 
                    user_data['user_id']
                )
                self.db_manager.create_job(job_data)
        
        # Test various query patterns
        query_tests = [
            ("get_all_users", lambda: self.db_manager.get_all_users()),
            ("get_all_jobs", lambda: self.db_manager.get_all_jobs()),
            ("get_user_jobs", lambda: self.db_manager.get_user_jobs('query_user_0')),
        ]
        
        for query_name, query_func in query_tests:
            start_time = time.time()
            result = query_func()
            execution_time = time.time() - start_time
            
            print(f"{query_name}: {execution_time:.6f}s, returned {len(result)} records")
            
            # Performance assertion
            self.assertLess(execution_time, 0.5, f"{query_name} query too slow")
    
    def test_database_transaction_performance(self):
        """Test performance of database transactions"""
        print("\n=== Testing Database Transaction Performance ===")
        
        num_operations = 50  # Reduced for faster testing
        
        # Test transaction performance
        start_time = time.time()
        
        for i in range(num_operations):
            user_data = TestDataFactory.create_user_data(f'trans_user_{i}')
            job_data = TestDataFactory.create_job_data(f'trans_job_{i}', user_data['user_id'])
            
            # Simulate transaction-like operations
            self.db_manager.create_user(user_data)
            self.db_manager.create_job(job_data)
            self.db_manager.update_job_status(job_data['job_id'], 'completed', 100)
        
        total_time = time.time() - start_time
        avg_time_per_transaction = total_time / num_operations
        
        print(f"Completed {num_operations} transactions in {total_time:.3f}s")
        print(f"Average time per transaction: {avg_time_per_transaction:.6f}s")
        
        # Performance assertions
        self.assertLess(total_time, 10.0, "Transaction processing took too long")
        self.assertLess(avg_time_per_transaction, 0.2, "Individual transactions too slow")


if __name__ == '__main__':
    unittest.main()