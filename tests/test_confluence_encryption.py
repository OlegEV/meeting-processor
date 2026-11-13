#!/usr/bin/env python3
"""
Fixed unit tests for Confluence encryption and security components
"""

import unittest
from unittest.mock import Mock, patch, mock_open
import tempfile
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from confluence_encryption import (
    ConfluenceTokenManager, ConfluenceTokenCLI, create_token_manager,
    EncryptionError, EncryptionKeyError, EncryptionDataError
)


class TestConfluenceTokenManager(unittest.TestCase):
    """Test cases for ConfluenceTokenManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.test_file.close()
        self.token_file_path = self.test_file.name
        
        self.manager = ConfluenceTokenManager(self.token_file_path)
        
        self.test_token = "test_api_token_12345"
        self.test_password = "secure_password_123"
        self.test_url = "https://test.atlassian.net/wiki"
        self.test_username = "test@example.com"
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.token_file_path)
        except FileNotFoundError:
            pass
    
    def test_token_manager_initialization(self):
        """Test ConfluenceTokenManager initialization"""
        self.assertEqual(str(self.manager.config_path), self.token_file_path)
        self.assertEqual(self.manager.salt_length, 32)
        self.assertEqual(self.manager.iterations, 100000)
    
    def test_generate_master_key(self):
        """Test master key generation"""
        password = "test_password"
        key1, salt1 = self.manager.generate_master_key(password)
        key2, salt2 = self.manager.generate_master_key(password)
        
        self.assertIsInstance(key1, bytes)
        self.assertIsInstance(salt1, bytes)
        self.assertNotEqual(salt1, salt2)  # Different salts
        self.assertNotEqual(key1, key2)    # Different keys due to different salts
        
        # Same password and salt should produce same key
        key3, _ = self.manager.generate_master_key(password, salt1)
        self.assertEqual(key1, key3)
    
    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption"""
        encrypted_data = self.manager.encrypt_token(self.test_token, self.test_password)
        
        self.assertIsInstance(encrypted_data, dict)
        self.assertIn('encrypted_token', encrypted_data)
        self.assertIn('salt', encrypted_data)
        self.assertIn('algorithm', encrypted_data)
        self.assertIn('iterations', encrypted_data)
        self.assertEqual(encrypted_data['algorithm'], 'PBKDF2-SHA256')
        self.assertEqual(encrypted_data['iterations'], 100000)
        
        decrypted_token = self.manager.decrypt_token(encrypted_data, self.test_password)
        self.assertEqual(decrypted_token, self.test_token)
    
    def test_decrypt_with_wrong_password(self):
        """Test decryption with wrong password"""
        encrypted_data = self.manager.encrypt_token(self.test_token, self.test_password)
        
        with self.assertRaises(EncryptionDataError):
            self.manager.decrypt_token(encrypted_data, "wrong_password")
    
    def test_decrypt_invalid_data(self):
        """Test decryption with invalid data"""
        invalid_data = {'invalid': 'data'}
        
        with self.assertRaises(EncryptionDataError):
            self.manager.decrypt_token(invalid_data, self.test_password)
    
    def test_save_and_load_encrypted_token(self):
        """Test saving and loading encrypted tokens"""
        # Save token
        success = self.manager.save_encrypted_token(
            token=self.test_token,
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        self.assertTrue(success)
        
        # Load token
        loaded_token = self.manager.load_encrypted_token(
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        self.assertEqual(loaded_token, self.test_token)
    
    def test_save_token_overwrites_existing(self):
        """Test that saving a token overwrites existing token"""
        # Save first token
        self.manager.save_encrypted_token(
            token="first_token",
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        # Save second token (should overwrite)
        self.manager.save_encrypted_token(
            token="second_token",
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        # Load token should return second token
        loaded_token = self.manager.load_encrypted_token(
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        self.assertEqual(loaded_token, "second_token")
    
    def test_load_nonexistent_token(self):
        """Test loading non-existent token"""
        loaded_token = self.manager.load_encrypted_token(
            password=self.test_password,
            confluence_url="https://nonexistent.atlassian.net/wiki",
            username="nonexistent@example.com"
        )
        
        self.assertIsNone(loaded_token)
    
    def test_load_token_wrong_password(self):
        """Test loading token with wrong password"""
        # Save token
        self.manager.save_encrypted_token(
            token=self.test_token,
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        # Try to load with wrong password
        loaded_token = self.manager.load_encrypted_token(
            password="wrong_password",
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        self.assertIsNone(loaded_token)
    
    def test_delete_token(self):
        """Test token deletion"""
        # Save token
        self.manager.save_encrypted_token(
            token=self.test_token,
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        # Verify token exists
        loaded_token = self.manager.load_encrypted_token(
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        self.assertEqual(loaded_token, self.test_token)
        
        # Delete token
        success = self.manager.delete_token(self.test_url, self.test_username)
        self.assertTrue(success)
        
        # Verify token is deleted
        loaded_token = self.manager.load_encrypted_token(
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        self.assertIsNone(loaded_token)
    
    def test_delete_nonexistent_token(self):
        """Test deleting non-existent token"""
        success = self.manager.delete_token(
            "https://nonexistent.atlassian.net/wiki",
            "nonexistent@example.com"
        )
        
        self.assertFalse(success)
    
    def test_list_saved_tokens(self):
        """Test listing saved tokens"""
        # Initially should be empty
        tokens = self.manager.list_saved_tokens()
        self.assertEqual(len(tokens), 0)
        
        # Save multiple tokens
        test_configs = [
            ("https://test1.atlassian.net/wiki", "user1@example.com"),
            ("https://test2.atlassian.net/wiki", "user2@example.com"),
            ("https://test1.atlassian.net/wiki", "user3@example.com")
        ]
        
        for url, username in test_configs:
            self.manager.save_encrypted_token(
                token=f"token_for_{username}",
                password=self.test_password,
                confluence_url=url,
                username=username
            )
        
        # List tokens
        tokens = self.manager.list_saved_tokens()
        self.assertEqual(len(tokens), 3)
        
        # Verify token information
        for token_info in tokens:
            self.assertIn('confluence_url', token_info)
            self.assertIn('username', token_info)
            self.assertIn('created_at', token_info)
    
    def test_validate_token_file_integrity(self):
        """Test token file integrity validation"""
        # Non-existent file should be valid
        os.unlink(self.token_file_path)  # Remove the empty file
        self.assertTrue(self.manager.validate_token_file_integrity())
        
        # Save a token
        self.manager.save_encrypted_token(
            token=self.test_token,
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        # File should still be valid
        self.assertTrue(self.manager.validate_token_file_integrity())
        
        # Corrupt the file
        with open(self.token_file_path, 'w') as f:
            f.write("invalid json")
        
        # File should be invalid
        self.assertFalse(self.manager.validate_token_file_integrity())
    
    def test_file_persistence(self):
        """Test that tokens persist across manager instances"""
        # Save token with first manager instance
        self.manager.save_encrypted_token(
            token=self.test_token,
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        # Create new manager instance with same file
        new_manager = ConfluenceTokenManager(self.token_file_path)
        
        # Load token with new manager
        loaded_token = new_manager.load_encrypted_token(
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        self.assertEqual(loaded_token, self.test_token)
    
    def test_multiple_users_same_url(self):
        """Test multiple users for same Confluence URL"""
        url = "https://shared.atlassian.net/wiki"
        users = ["user1@example.com", "user2@example.com", "user3@example.com"]
        
        # Save tokens for multiple users
        for i, username in enumerate(users):
            self.manager.save_encrypted_token(
                token=f"token_{i+1}",
                password=self.test_password,
                confluence_url=url,
                username=username
            )
        
        # Verify each user can load their own token
        for i, username in enumerate(users):
            loaded_token = self.manager.load_encrypted_token(
                password=self.test_password,
                confluence_url=url,
                username=username
            )
            self.assertEqual(loaded_token, f"token_{i+1}")
    
    def test_same_user_multiple_urls(self):
        """Test same user with multiple Confluence URLs"""
        username = "user@example.com"
        urls = [
            "https://company1.atlassian.net/wiki",
            "https://company2.atlassian.net/wiki",
            "https://company3.atlassian.net/wiki"
        ]
        
        # Save tokens for multiple URLs
        for i, url in enumerate(urls):
            self.manager.save_encrypted_token(
                token=f"token_{i+1}",
                password=self.test_password,
                confluence_url=url,
                username=username
            )
        
        # Verify user can load tokens for each URL
        for i, url in enumerate(urls):
            loaded_token = self.manager.load_encrypted_token(
                password=self.test_password,
                confluence_url=url,
                username=username
            )
            self.assertEqual(loaded_token, f"token_{i+1}")


class TestConfluenceTokenCLI(unittest.TestCase):
    """Test cases for ConfluenceTokenCLI"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.test_file.close()
        self.token_file_path = self.test_file.name
        
        self.token_manager = ConfluenceTokenManager(self.token_file_path)
        self.cli = ConfluenceTokenCLI(self.token_manager)
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.token_file_path)
        except FileNotFoundError:
            pass
    
    def test_cli_initialization(self):
        """Test ConfluenceTokenCLI initialization"""
        self.assertIsInstance(self.cli.token_manager, ConfluenceTokenManager)
    
    @patch('builtins.input')
    @patch('getpass.getpass')
    @patch('builtins.print')
    def test_add_token_interactive_success(self, mock_print, mock_getpass, mock_input):
        """Test adding token interactively - success case"""
        # Mock user inputs
        mock_input.side_effect = [
            'https://test.atlassian.net/wiki',  # URL
            'test@example.com',                 # Username
        ]
        mock_getpass.side_effect = [
            'test_api_token_123',               # API Token
            'secure_password',                  # Password
            'secure_password'                   # Password confirmation
        ]
        
        # Add token
        success = self.cli.add_token_interactive()
        
        self.assertTrue(success)
        
        # Verify token was saved
        loaded_token = self.token_manager.load_encrypted_token(
            password='secure_password',
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com'
        )
        
        self.assertEqual(loaded_token, 'test_api_token_123')
    
    @patch('builtins.input')
    @patch('getpass.getpass')
    @patch('builtins.print')
    def test_add_token_interactive_password_mismatch(self, mock_print, mock_getpass, mock_input):
        """Test adding token with password mismatch"""
        mock_input.side_effect = [
            'https://test.atlassian.net/wiki',
            'test@example.com',
        ]
        mock_getpass.side_effect = [
            'test_api_token_123',
            'password1',
            'password2'  # Different password
        ]
        
        success = self.cli.add_token_interactive()
        
        self.assertFalse(success)
    
    def test_list_tokens_empty(self):
        """Test listing tokens when none are stored"""
        with patch('builtins.print') as mock_print:
            self.cli.list_tokens()
            mock_print.assert_called_with("📝 Сохраненных токенов нет")
    
    def test_list_tokens_with_data(self):
        """Test listing tokens when some are stored"""
        # Add a token first
        self.token_manager.save_encrypted_token(
            token='test_token',
            password='password',
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com'
        )
        
        with patch('builtins.print') as mock_print:
            self.cli.list_tokens()
            
            # Check that print was called with token information
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any('test@example.com' in call for call in calls))
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_delete_token_interactive_success(self, mock_print, mock_input):
        """Test deleting token interactively - success case"""
        # First add a token
        self.token_manager.save_encrypted_token(
            token='test_token',
            password='password',
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com'
        )
        
        # Mock user inputs for deletion
        mock_input.side_effect = [
            '1',  # Select first token
            'y'   # Confirm deletion
        ]
        
        success = self.cli.delete_token_interactive()
        
        self.assertTrue(success)
        
        # Verify token was deleted
        loaded_token = self.token_manager.load_encrypted_token(
            password='password',
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com'
        )
        
        self.assertIsNone(loaded_token)


class TestCreateTokenManager(unittest.TestCase):
    """Test cases for create_token_manager factory function"""
    
    def test_create_token_manager_default_path(self):
        """Test creating token manager with default path"""
        manager = create_token_manager()
        
        self.assertIsInstance(manager, ConfluenceTokenManager)
        self.assertTrue(str(manager.config_path).endswith('confluence_tokens.json'))
    
    def test_create_token_manager_custom_path(self):
        """Test creating token manager with custom path"""
        custom_path = 'custom_tokens.json'
        manager = create_token_manager(custom_path)
        
        self.assertIsInstance(manager, ConfluenceTokenManager)
        self.assertEqual(str(manager.config_path), custom_path)


class TestSecurityFeatures(unittest.TestCase):
    """Test cases for security features"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.test_file.close()
        self.token_file_path = self.test_file.name
        
        self.manager = ConfluenceTokenManager(self.token_file_path)
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.token_file_path)
        except FileNotFoundError:
            pass
    
    def test_password_salt_uniqueness(self):
        """Test that each token gets a unique salt"""
        token1 = "token1"
        token2 = "token2"
        password = "same_password"
        
        encrypted1 = self.manager.encrypt_token(token1, password)
        encrypted2 = self.manager.encrypt_token(token2, password)
        
        # Salts should be different
        self.assertNotEqual(encrypted1['salt'], encrypted2['salt'])
        
        # Encrypted tokens should be different even with same password
        self.assertNotEqual(encrypted1['encrypted_token'], encrypted2['encrypted_token'])
    
    def test_token_not_stored_in_plaintext(self):
        """Test that tokens are never stored in plaintext"""
        self.manager.save_encrypted_token(
            token="secret_token",
            password="password",
            confluence_url="https://test.atlassian.net/wiki",
            username="test@example.com"
        )
        
        # Read the file directly and verify token is not in plaintext
        with open(self.token_file_path, 'r') as f:
            file_content = f.read()
        
        self.assertNotIn("secret_token", file_content)
    
    def test_password_not_stored(self):
        """Test that passwords are never stored"""
        self.manager.save_encrypted_token(
            token="secret_token",
            password="secret_password",
            confluence_url="https://test.atlassian.net/wiki",
            username="test@example.com"
        )
        
        # Read the file directly and verify password is not stored
        with open(self.token_file_path, 'r') as f:
            file_content = f.read()
        
        self.assertNotIn("secret_password", file_content)
    
    def test_encryption_strength(self):
        """Test encryption produces sufficiently random output"""
        token = "test_token"
        password = "test_password"
        
        # Encrypt same token multiple times
        encrypted_tokens = []
        for _ in range(10):
            encrypted_data = self.manager.encrypt_token(token, password)
            encrypted_tokens.append(encrypted_data['encrypted_token'])
        
        # All encrypted versions should be different (due to unique salts)
        self.assertEqual(len(set(encrypted_tokens)), 10)


if __name__ == '__main__':
    unittest.main()