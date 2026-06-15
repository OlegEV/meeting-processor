#!/usr/bin/env python3
"""
Unit tests for is_current_user_admin()
"""

import unittest
import sys
import os
from unittest.mock import MagicMock

# Stub out packages that may not be installed in the test environment
for _mod in ('jwt', 'flask', 'werkzeug', 'werkzeug.exceptions'):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth.decorators as decorators_module
from auth.decorators import is_current_user_admin, init_auth_decorators
from auth.user_context import UserContext


class TestIsCurrentUserAdmin(unittest.TestCase):

    def setUp(self):
        decorators_module._auth_decorators = None
        UserContext.clear_current_user()

    def tearDown(self):
        decorators_module._auth_decorators = None
        UserContext.clear_current_user()

    def test_returns_false_when_not_initialized(self):
        self.assertFalse(is_current_user_admin())

    def test_returns_false_when_admin_user_ids_empty(self):
        init_auth_decorators(None, {'auth': {'admin_user_ids': []}})
        UserContext.set_current_user({'user_id': 'user1'})
        self.assertFalse(is_current_user_admin())

    def test_returns_true_when_user_in_admin_ids(self):
        init_auth_decorators(None, {'auth': {'admin_user_ids': ['admin1', 'admin2']}})
        UserContext.set_current_user({'user_id': 'admin1'})
        self.assertTrue(is_current_user_admin())

    def test_returns_false_when_user_not_in_admin_ids(self):
        init_auth_decorators(None, {'auth': {'admin_user_ids': ['admin1']}})
        UserContext.set_current_user({'user_id': 'regular_user'})
        self.assertFalse(is_current_user_admin())


if __name__ == '__main__':
    unittest.main()
