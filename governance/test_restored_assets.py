import os
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from governance.management.commands.check_restored_assets import local_restore_target


class RestoreTargetTests(SimpleTestCase):
    def test_only_explicit_local_restore_namespace_is_allowed(self):
        with patch.dict(os.environ, {'CI': ''}):
            self.assertTrue(local_restore_target('postgresql', {'HOST': '127.0.0.1', 'NAME': 'anthec_restore_20261021'}, False))
            for name in ('anthec_owner_testing', 'tighri', 'antheec_restore_test', 'anthec_restore_', 'anthec_restore_../source'):
                self.assertFalse(local_restore_target('postgresql', {'HOST': 'localhost', 'NAME': name}, False))
        for vendor, host, hosted in (('sqlite', 'localhost', False), ('postgresql', 'db.internal', False), ('postgresql', 'localhost', True)):
            self.assertFalse(local_restore_target(vendor, {'HOST': host, 'NAME': 'anthec_restore_20261021'}, hosted))


class RestoreCommandGuards(TestCase):
    def test_default_and_actual_test_database_are_refused(self):
        for options in ({}, {'allow_local_restore': True}):
            with self.assertRaisesMessage(CommandError, 'hosted/source databases refused'):
                call_command('check_restored_assets', **options)
