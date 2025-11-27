#!/usr/bin/env python3
"""
Comprehensive unit tests for Confluence encryption and security components
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
        self.assertEqual(self.manager.token_file_path, self.token_file_path)
        self.assertIsInstance(self.manager.tokens, dict)
    
    def test_generate_salt(self):
        """Test salt generation"""
        salt1 = self.manager._generate_salt()
        salt2 = self.manager._generate_salt()
        
        self.assertIsInstance(salt1, str)
        self.assertIsInstance(salt2, str)
        self.assertNotEqual(salt1, salt2)
        self.assertGreater(len(salt1), 0)
        self.assertGreater(len(salt2), 0)
    
    def test_derive_key_from_password(self):
        """Test key derivation from password"""
        salt = "test_salt"
        key1 = self.manager._derive_key_from_password(self.test_password, salt)
        key2 = self.manager._derive_key_from_password(self.test_password, salt)
        
        self.assertEqual(key1, key2)
        self.assertIsInstance(key1, str)
        self.assertGreater(len(key1), 0)
        
        # Different password should produce different key
        key3 = self.manager._derive_key_from_password("different_password", salt)
        self.assertNotEqual(key1, key3)
        
        # Different salt should produce different key
        key4 = self.manager._derive_key_from_password(self.test_password, "different_salt")
        self.assertNotEqual(key1, key4)
    
    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption"""
        password = self.test_password
        
        encrypted_data = self.manager.encrypt_token(self.test_token, password)
        
        self.assertIsInstance(encrypted_data, dict)
        self.assertIn('encrypted_token', encrypted_data)
        self.assertIn('salt', encrypted_data)
        self.assertNotEqual(encrypted_data['encrypted_token'], self.test_token)
        
        decrypted_token = self.manager.decrypt_token(encrypted_data, password)
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
    
    def test_list_stored_tokens(self):
        """Test listing stored tokens"""
        # Initially should be empty
        tokens = self.manager.list_stored_tokens()
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
        tokens = self.manager.list_stored_tokens()
        self.assertEqual(len(tokens), 3)
        
        # Verify token information
        for token_info in tokens:
            self.assertIn('confluence_url', token_info)
            self.assertIn('username', token_info)
            self.assertIn('created_at', token_info)
            self.assertNotIn('encrypted_token', token_info)  # Should not expose encrypted data
    
    def test_get_token_info(self):
        """Test getting token information"""
        # Save token
        self.manager.save_encrypted_token(
            token=self.test_token,
            password=self.test_password,
            confluence_url=self.test_url,
            username=self.test_username
        )
        
        # Get token info
        token_info = self.manager.get_token_info(self.test_url, self.test_username)
        
        self.assertIsNotNone(token_info)
        self.assertEqual(token_info['confluence_url'], self.test_url)
        self.assertEqual(token_info['username'], self.test_username)
        self.assertIn('created_at', token_info)
        self.assertNotIn('encrypted_token', token_info)
    
    def test_get_nonexistent_token_info(self):
        """Test getting info for non-existent token"""
        token_info = self.manager.get_token_info(
            "https://nonexistent.atlassian.net/wiki",
            "nonexistent@example.com"
        )
        
        self.assertIsNone(token_info)
    
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
    
    def test_file_corruption_handling(self):
        """Test handling of corrupted token file"""
        # Write invalid JSON to file
        with open(self.token_file_path, 'w') as f:
            f.write("invalid json content")
        
        # Creating manager should handle corruption gracefully
        manager = ConfluenceTokenManager(self.token_file_path)
        self.assertIsInstance(manager.tokens, dict)
        self.assertEqual(len(manager.tokens), 0)
    
    def test_file_permissions_error(self):
        """Test handling of file permission errors"""
        # Create a directory where file should be (to cause permission error)
        os.unlink(self.token_file_path)
        os.makedirs(self.token_file_path)
        
        try:
            # This should handle the error gracefully
            manager = ConfluenceTokenManager(self.token_file_path)
            
            # Saving should fail gracefully
            success = manager.save_encrypted_token(
                token=self.test_token,
                password=self.test_password,
                confluence_url=self.test_url,
                username=self.test_username
            )
            
            self.assertFalse(success)
        finally:
            # Clean up
            try:
                os.rmdir(self.token_file_path)
            except:
                pass
    
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
        
        self.cli = ConfluenceTokenCLI(self.token_file_path)
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.token_file_path)
        except FileNotFoundError:
            pass
    
    def test_cli_initialization(self):
        """Test ConfluenceTokenCLI initialization"""
        self.assertIsInstance(self.cli.token_manager, ConfluenceTokenManager)
        self.assertEqual(self.cli.token_manager.token_file_path, self.token_file_path)
    
    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_add_token_interactive(self, mock_getpass, mock_input):
        """Test adding token interactively"""
        # Mock user inputs
        mock_input.side_effect = [
            'https://test.atlassian.net/wiki',  # URL
            'test@example.com',                 # Username
            'test_api_token_123'                # API Token
        ]
        mock_getpass.return_value = 'secure_password'  # Password
        
        # Add token
        success = self.cli.add_token()
        
        self.assertTrue(success)
        
        # Verify token was saved
        loaded_token = self.cli.token_manager.load_encrypted_token(
            password='secure_password',
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com'
        )
        
        self.assertEqual(loaded_token, 'test_api_token_123')
    
    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_add_token_with_parameters(self, mock_getpass, mock_input):
        """Test adding token with command line parameters"""
        mock_getpass.return_value = 'secure_password'
        
        success = self.cli.add_token(
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='test_api_token_123'
        )
        
        self.assertTrue(success)
        
        # Verify token was saved
        loaded_token = self.cli.token_manager.load_encrypted_token(
            password='secure_password',
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com'
        )
        
        self.assertEqual(loaded_token, 'test_api_token_123')
    
    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_get_token(self, mock_getpass, mock_input):
        """Test getting stored token"""
        # First add a token
        mock_getpass.return_value = 'secure_password'
        self.cli.add_token(
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='test_api_token_123'
        )
        
        # Mock inputs for getting token
        mock_input.side_effect = [
            'https://test.atlassian.net/wiki',  # URL
            'test@example.com'                  # Username
        ]
        mock_getpass.return_value = 'secure_password'  # Password
        
        # Get token
        token = self.cli.get_token()
        
        self.assertEqual(token, 'test_api_token_123')
    
    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_get_token_with_parameters(self, mock_getpass, mock_input):
        """Test getting token with command line parameters"""
        # First add a token
        mock_getpass.return_value = 'secure_password'
        self.cli.add_token(
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='test_api_token_123'
        )
        
        # Get token with parameters
        mock_getpass.return_value = 'secure_password'
        token = self.cli.get_token(
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com'
        )
        
        self.assertEqual(token, 'test_api_token_123')
    
    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_get_nonexistent_token(self, mock_getpass, mock_input):
        """Test getting non-existent token"""
        mock_input.side_effect = [
            'https://nonexistent.atlassian.net/wiki',
            'nonexistent@example.com'
        ]
        mock_getpass.return_value = 'password'
        
        token = self.cli.get_token()
        
        self.assertIsNone(token)
    
    def test_list_tokens_empty(self):
        """Test listing tokens when none are stored"""
        tokens = self.cli.list_tokens()
        
        self.assertEqual(len(tokens), 0)
    
    @patch('getpass.getpass')
    def test_list_tokens_with_data(self, mock_getpass):
        """Test listing tokens when some are stored"""
        mock_getpass.return_value = 'secure_password'
        
        # Add multiple tokens
        test_configs = [
            ('https://test1.atlassian.net/wiki', 'user1@example.com', 'token1'),
            ('https://test2.atlassian.net/wiki', 'user2@example.com', 'token2'),
            ('https://test1.atlassian.net/wiki', 'user3@example.com', 'token3')
        ]
        
        for url, username, token in test_configs:
            self.cli.add_token(
                confluence_url=url,
                username=username,
                api_token=token
            )
        
        # List tokens
        tokens = self.cli.list_tokens()
        
        self.assertEqual(len(tokens), 3)
        
        # Verify token information
        urls = [token['confluence_url'] for token in tokens]
        usernames = [token['username'] for token in tokens]
        
        self.assertIn('https://test1.atlassian.net/wiki', urls)
        self.assertIn('https://test2.atlassian.net/wiki', urls)
        self.assertIn('user1@example.com', usernames)
        self.assertIn('user2@example.com', usernames)
        self.assertIn('user3@example.com', usernames)
    
    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_delete_token(self, mock_getpass, mock_input):
        """Test deleting stored token"""
        # First add a token
        mock_getpass.return_value = 'secure_password'
        self.cli.add_token(
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com',
            api_token='test_api_token_123'
        )
        
        # Mock inputs for deleting token
        mock_input.side_effect = [
            'https://test.atlassian.net/wiki',  # URL
            'test@example.com'                  # Username
        ]
        
        # Delete token
        success = self.cli.delete_token()
        
        self.assertTrue(success)
        
        # Verify token was deleted
        mock_getpass.return_value = 'secure_password'
        token = self.cli.get_token(
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com'
        )
        
        self.assertIsNone(token)
    
    @patch('builtins.input')
    def test_delete_token_with_parameters(self, mock_input):
        """Test deleting token with command line parameters"""
        # First add a token
        with patch('getpass.getpass', return_value='secure_password'):
            self.cli.add_token(
                confluence_url='https://test.atlassian.net/wiki',
                username='test@example.com',
                api_token='test_api_token_123'
            )
        
        # Delete token with parameters
        success = self.cli.delete_token(
            confluence_url='https://test.atlassian.net/wiki',
            username='test@example.com'
        )
        
        self.assertTrue(success)
    
    @patch('builtins.input')
    def test_delete_nonexistent_token(self, mock_input):
        """Test deleting non-existent token"""
        mock_input.side_effect = [
            'https://nonexistent.atlassian.net/wiki',
            'nonexistent@example.com'
        ]
        
        success = self.cli.delete_token()
        
        self.assertFalse(success)


class TestCreateTokenManager(unittest.TestCase):
    """Test cases for create_token_manager factory function"""
    
    def test_create_token_manager_default_path(self):
        """Test creating token manager with default path"""
        manager = create_token_manager()
        
        self.assertIsInstance(manager, ConfluenceTokenManager)
        self.assertTrue(manager.token_file_path.endswith('confluence_tokens.json'))
    
    def test_create_token_manager_custom_path(self):
        """Test creating token manager with custom path"""
        custom_path = 'custom_tokens.json'
        manager = create_token_manager(custom_path)
        
        self.assertIsInstance(manager, ConfluenceTokenManager)
        self.assertEqual(manager.token_file_path, custom_path)
    
    def test_create_token_manager_with_directory(self):
        """Test creating token manager with directory path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = create_token_manager(temp_dir)
            
            self.assertIsInstance(manager, ConfluenceTokenManager)
            expected_path = os.path.join(temp_dir, 'confluence_tokens.json')
            self.assertEqual(manager.token_file_path, expected_path)


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
    
    def test_key_derivation_consistency(self):
        """Test that key derivation is consistent"""
        password = "test_password"
        salt = "test_salt"
        
        # Derive key multiple times
        keys = []
        for _ in range(5):
            key = self.manager._derive_key_from_password(password, salt)
            keys.append(key)
        
        # All keys should be identical
        self.assertEqual(len(set(keys)), 1)
    
    def test_file_format_security(self):
        """Test that file format doesn't expose sensitive information"""
        self.manager.save_encrypted_token(
            token="secret_token",
            password="secret_password",
            confluence_url="https://test.atlassian.net/wiki",
            username="test@example.com"
        )
        
        # Load and parse the file
        with open(self.token_file_path, 'r') as f:
            data = json.load(f)
        
        # Verify structure doesn't expose sensitive data
        for key, token_data in data.items():
            self.assertIn('encrypted_token', token_data)
            self.assertIn('salt', token_data)
            self.assertIn('confluence_url', token_data)
            self.assertIn('username', token_data)
            self.assertIn('created_at', token_data)
            
            # Should not contain plaintext sensitive data
            self.assertNotIn('password', token_data)
            self.assertNotIn('api_token', token_data)
            self.assertNotIn('token', token_data)


if __name__ == '__main__':
    unittest.main()