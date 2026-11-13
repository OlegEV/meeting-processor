#!/usr/bin/env python3
"""
Security tests for token encryption, access control, and security measures
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import gc
import os
import sys
import json
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from confluence_encryption import ConfluenceTokenManager, EncryptionDataError
from confluence_client import ConfluenceEncryption
from run_web import WorkingMeetingWebApp


class TestTokenEncryptionSecurity(unittest.TestCase):
    """Security tests for token encryption"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.test_file.close()
        self.token_file_path = self.test_file.name
        
        self.manager = ConfluenceTokenManager(self.token_file_path)
        
        self.test_token = "very_secret_api_token_12345"
        self.test_password = "super_secure_password_123"
        self.weak_password = "123"
        self.test_url = "https://test.atlassian.net/wiki"
        self.test_username = "test@example.com"
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.token_file_path)
        except FileNotFoundError:
            pass
    
    def test_encryption_key_strength(self):
        """Test that encryption keys are cryptographically strong"""
        # Test multiple key generations
        keys = []
        for _ in range(10):
            key = ConfluenceEncryption.generate_key()
            keys.append(key)
            
            # Key should be base64 encoded
            import base64
            try:
                decoded = base64.urlsafe_b64decode(key.encode())
                self.assertEqual(len(decoded), 32)  # 256-bit key
            except Exception:
                self.fail(f"Generated key is not valid base64: {key}")
        
        # All keys should be unique
        self.assertEqual(len(set(keys)), 10)
    
    def test_password_based_key_derivation_security(self):
        """Test security of password-based key derivation"""
        password = "test_password"
        salt1 = "salt1"
        salt2 = "salt2"
        
        # Same password + salt should produce same key
        key1a = ConfluenceEncryption.derive_key_from_password(password, salt1)
        key1b = ConfluenceEncryption.derive_key_from_password(password, salt1)
        self.assertEqual(key1a, key1b)
        
        # Different salts should produce different keys
        key2 = ConfluenceEncryption.derive_key_from_password(password, salt2)
        self.assertNotEqual(key1a, key2)
        
        # Key should be proper length
        import base64
        decoded_key = base64.urlsafe_b64decode(key1a.encode())
        self.assertEqual(len(decoded_key), 32)  # 256-bit key
    
    def test_encryption_randomness(self):
        """Test that encryption produces random output"""
        token = "same_token"
        password = "same_password"
        
        # Encrypt same token multiple times
        encrypted_results = [self.manager.encrypt_token(token, password) for _ in range(10)]

        # All encrypted results should be different (due to random salts)
        self.assertEqual(len({data['encrypted_token'] for data in encrypted_results}), 10)

        # All should decrypt to same original token
        for encrypted_data in encrypted_results:
            self.assertEqual(self.manager.decrypt_token(encrypted_data, password), token)

    def test_salt_randomness(self):
        """Test that salts are properly random"""
        salts = []
        for _ in range(20):
            _, salt = self.manager.generate_master_key("same_password")
            salts.append(salt)

            # Salt should be reasonable length
            self.assertGreaterEqual(len(salt), 16)

        # All salts should be unique
        self.assertEqual(len(set(salts)), 20)
    
    def test_encryption_with_weak_password(self):
        """Test encryption behavior with weak passwords"""
        weak_passwords = ["", "1", "12", "123", "password", "admin"]
        
        for weak_pwd in weak_passwords:
            # Encryption should still work (no password strength enforcement in encryption layer)
            encrypted_data = self.manager.encrypt_token(self.test_token, weak_pwd)
            self.assertIsInstance(encrypted_data, dict)
            self.assertIn('encrypted_token', encrypted_data)
            self.assertIn('salt', encrypted_data)
            
            # Should be able to decrypt
            decrypted = self.manager.decrypt_token(encrypted_data, weak_pwd)
            self.assertEqual(decrypted, self.test_token)
    
    def test_wrong_password_is_rejected(self):
        """Test that a token cannot be decrypted with a wrong password"""
        encrypted_data = self.manager.encrypt_token(self.test_token, "correct_password")

        with self.assertRaises(EncryptionDataError):
            self.manager.decrypt_token(encrypted_data, "wrong_password")

    def test_encrypted_data_format_security(self):
        """Test that encrypted data format doesn't leak information"""
        tokens = ["short", "medium_length_token", "very_long_token_that_is_much_longer_than_others"]
        password = "test_password"
        
        encrypted_lengths = []
        for token in tokens:
            encrypted_data = self.manager.encrypt_token(token, password)
            encrypted_lengths.append(len(encrypted_data['encrypted_token']))
        
        # Encrypted lengths should not directly correlate with plaintext lengths
        # (due to padding and encoding)
        self.assertNotEqual(encrypted_lengths[0], len(tokens[0]))
        self.assertNotEqual(encrypted_lengths[1], len(tokens[1]))
        self.assertNotEqual(encrypted_lengths[2], len(tokens[2]))
    
    def test_key_derivation_iterations(self):
        """Test that key derivation uses sufficient iterations"""
        # This tests the PBKDF2 iteration count indirectly by measuring time
        password = "test_password"
        salt = "test_salt"
        
        start_time = time.time()
        key = ConfluenceEncryption.derive_key_from_password(password, salt)
        derivation_time = time.time() - start_time
        
        # Key derivation should take some time (indicating sufficient iterations)
        # This is a basic check - should take at least a few milliseconds
        self.assertGreater(derivation_time, 0.001)  # At least 1ms
        
        # Verify key is valid
        self.assertIsInstance(key, str)
        self.assertGreater(len(key), 0)


class TestAccessControlSecurity(unittest.TestCase):
    """Security tests for access control mechanisms"""
    
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
                'debug_mode': False,  # Disable debug mode for security testing
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
        
        # Create test users
        self.user1_id = 'security_user_1'
        self.user2_id = 'security_user_2'
        
        self.user1_data = {
            'user_id': self.user1_id,
            'email': 'user1@example.com',
            'name': 'Security User 1'
        }
        
        self.user2_data = {
            'user_id': self.user2_id,
            'email': 'user2@example.com',
            'name': 'Security User 2'
        }
        
        self.app.db_manager.create_user(self.user1_data)
        self.app.db_manager.create_user(self.user2_data)
    
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

    def login(self, user_data):
        """Makes the token validator accept requests as the given user until the test ends"""
        patcher = patch.object(self.app.token_validator, 'validate_request',
                               return_value=(True, dict(user_data), None))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_unauthorized_access_prevention(self):
        """Test that unauthorized access is properly prevented"""
        # Test accessing protected endpoints without authentication
        protected_endpoints = [
            '/',
            '/jobs',
            '/statistics',
            '/status/test_job',
            '/api/status/test_job'
        ]
        
        for endpoint in protected_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                # Should return 401 or redirect (302)
                self.assertIn(response.status_code, [401, 302])
    
    def test_public_direct_result_links(self):
        """Protocol and transcript links work without authentication"""
        job_id = '3fa85f64-5717-4562-b3fc-2c963f66afa6'
        with tempfile.TemporaryDirectory() as temp_dir:
            transcript_path = os.path.join(temp_dir, 'transcript.txt')
            summary_path = os.path.join(temp_dir, 'summary.md')
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write('Public transcript')
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write('# Public protocol')

            self.app.db_manager.create_job({
                'job_id': job_id,
                'user_id': self.user1_id,
                'filename': 'public_meeting.mp3',
                'template': 'standard',
                'status': 'completed',
                'progress': 100,
                'transcript_file': transcript_path,
                'summary_file': summary_path
            })

            for endpoint in (
                f'/download/{job_id}/transcript',
                f'/download/{job_id}/summary',
                f'/view/{job_id}/transcript',
                f'/view/{job_id}/summary'
            ):
                with self.subTest(endpoint=endpoint):
                    response = self.client.get(endpoint)
                    self.assertEqual(response.status_code, 200)

    def test_invalid_token_rejection(self):
        """Test that invalid tokens are properly rejected"""
        invalid_tokens = [
            'invalid_token',
            'expired_token',
            '',
            'malformed.token.here',
            'Bearer invalid_token',
            '../../etc/passwd',
            '<script>alert("xss")</script>',
            'null',
            'undefined'
        ]
        
        for token in invalid_tokens:
            with self.subTest(token=token):
                headers = {'X-Identity-Token': token}
                response = self.client.get('/', headers=headers)
                # Should return 401 or redirect
                self.assertIn(response.status_code, [401, 302])
    
    def test_user_data_isolation(self):
        """Test that users can only access their own data"""
        # Create jobs for both users
        job1_data = {
            'job_id': 'user1_job',
            'user_id': self.user1_id,
            'filename': 'user1_meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        
        job2_data = {
            'job_id': 'user2_job',
            'user_id': self.user2_id,
            'filename': 'user2_meeting.mp3',
            'template': 'standard',
            'status': 'completed',
            'progress': 100
        }
        
        self.app.db_manager.create_job(job1_data)
        self.app.db_manager.create_job(job2_data)

        self.login(self.user1_data)
        user1_headers = {'X-Identity-Token': 'user1_token'}

        # User 1 can access their own job
        response = self.client.get('/api/status/user1_job', headers=user1_headers)
        self.assertEqual(response.status_code, 200)

        # User 1 tries to access User 2's job
        response = self.client.get('/status/user2_job', headers=user1_headers)
        # Should be denied (redirect or 404)
        self.assertIn(response.status_code, [302, 404])
        
        # User 1 tries to access User 2's job via API
        response = self.client.get('/api/status/user2_job', headers=user1_headers)
        # Should be denied
        self.assertEqual(response.status_code, 404)
    
    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection attacks"""
        # SQL injection attempts in various parameters
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'hack@evil.com'); --",
            "' OR 1=1 --",
            "admin'--",
            "' OR 'x'='x",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        self.login(self.user1_data)
        user_headers = {'X-Identity-Token': 'test_token'}

        for payload in sql_injection_payloads:
            with self.subTest(payload=payload):
                # Test in job_id parameter
                response = self.client.get(f'/status/{payload}', headers=user_headers)
                # Should not cause server error (500)
                self.assertNotEqual(response.status_code, 500)
                
                # Test in API endpoint
                response = self.client.get(f'/api/status/{payload}', headers=user_headers)
                self.assertNotEqual(response.status_code, 500)

        # The users table is intact
        self.assertIsNotNone(self.app.db_manager.get_user_by_id(self.user1_id))
        self.assertIsNotNone(self.app.db_manager.get_user_by_id(self.user2_id))
        self.assertIsNone(self.app.db_manager.get_user_by_id('hacker'))

    def test_xss_prevention(self):
        """Test prevention of Cross-Site Scripting (XSS) attacks"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "';alert('xss');//",
            "<iframe src=javascript:alert('xss')></iframe>",
            "<%2Fscript%3E%3Cscript%3Ealert('xss')%3C%2Fscript%3E"
        ]
        
        self.login(self.user1_data)
        user_headers = {'X-Identity-Token': 'test_token'}

        # Create job with XSS payload in filename
        for i, payload in enumerate(xss_payloads):
            with self.subTest(payload=payload):
                job_data = {
                    'job_id': f'xss_test_job_{i}',
                    'user_id': self.user1_id,
                    'filename': payload,
                    'template': 'standard',
                    'status': 'completed',
                    'progress': 100,
                    'message': payload
                }

                self.app.db_manager.create_job(job_data)

                # Get status page
                response = self.client.get(f'/status/xss_test_job_{i}', headers=user_headers)
                self.assertEqual(response.status_code, 200)

                # The payload must never appear unescaped in the page
                response_text = response.data.decode('utf-8')
                if '<' in payload:
                    self.assertNotIn(payload, response_text)
    
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks"""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd"
        ]
        
        self.login(self.user1_data)
        user_headers = {'X-Identity-Token': 'test_token'}

        for payload in path_traversal_payloads:
            with self.subTest(payload=payload):
                # Test in various endpoints
                endpoints = [
                    f'/status/{payload}',
                    f'/download/{payload}/transcript',
                    f'/view/{payload}/summary'
                ]
                
                for endpoint in endpoints:
                    response = self.client.get(endpoint, headers=user_headers)
                    # No job matches the payload, so no file may be served
                    self.assertNotEqual(response.status_code, 200)
                    self.assertNotEqual(response.status_code, 500)

    def test_sensitive_data_exposure_prevention(self):
        """Test that sensitive data is not exposed in responses"""
        self.login(self.user1_data)
        user_headers = {'X-Identity-Token': 'test_token'}

        # Test various endpoints for sensitive data exposure
        endpoints = [
            '/health',
            '/',
            '/jobs'
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint, headers=user_headers)
                self.assertEqual(response.status_code, 200)

                # Secrets from the configuration must never reach a response
                response_text = response.data.decode('utf-8').lower()
                self.assertNotIn('test_deepgram_key', response_text)
                self.assertNotIn('test_claude_key', response_text)
                self.assertNotIn('test_secret_key', response_text)
                self.assertNotIn('test_token_123', response_text)


if __name__ == '__main__':
    unittest.main()