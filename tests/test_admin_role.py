#!/usr/bin/env python3
"""
Unit tests for is_current_user_admin()
"""

import importlib.util
import unittest
import sys
import os
from unittest.mock import MagicMock

# Stub out packages only when they are really missing: an unconditional stub
# would replace the real flask/werkzeug for every test module collected later
for _pkg, _mods in (('jwt', ('jwt',)),
                    ('flask', ('flask',)),
                    ('werkzeug', ('werkzeug', 'werkzeug.exceptions'))):
    if importlib.util.find_spec(_pkg) is None:
        for _mod in _mods:
            sys.modules.setdefault(_mod, MagicMock())

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

    def test_returns_false_when_admin_emails_empty(self):
        init_auth_decorators(None, {'auth': {'admin_emails': []}})
        UserContext.set_current_user({'user_id': 'user1', 'email': 'user@example.com'})
        self.assertFalse(is_current_user_admin())

    def test_returns_true_when_email_in_admin_emails(self):
        init_auth_decorators(None, {'auth': {'admin_emails': ['admin@example.com', 'admin2@example.com']}})
        UserContext.set_current_user({'user_id': 'admin1', 'email': 'admin@example.com'})
        self.assertTrue(is_current_user_admin())

    def test_returns_false_when_email_not_in_admin_emails(self):
        init_auth_decorators(None, {'auth': {'admin_emails': ['admin@example.com']}})
        UserContext.set_current_user({'user_id': 'user1', 'email': 'user@example.com'})
        self.assertFalse(is_current_user_admin())


if __name__ == '__main__':
    unittest.main()
