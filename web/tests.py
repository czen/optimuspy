import requests
from django.conf import settings
from django.test import TestCase
from django.test.runner import DiscoverRunner

# Create your tests here.

# pylint: disable=import-outside-toplevel, global-statement

import django
django.setup()

TOKEN: str = None


def setUpModule():
    global TOKEN
    from web.models import User
    u = User.objects.create_user(username='unittest', password='123')
    TOKEN = u.api.key


def tearDownModule():
    from web.models import User
    User.objects.get(username='unittest').delete()


class ProductionDBTestRunner(DiscoverRunner):
    """Custom test runner to do testing on live database :P"""

    def setup_databases(self, **kwargs):
        pass

    def teardown_databases(self, *args, **kwargs):
        pass


class AuthTests(TestCase):
    def test_invalid_params(self):
        data = {
            'username': '123'
        }
        try:
            r = requests.post('http://localhost:8000/api/auth/', json=data, timeout=60)
            json = r.json()
            self.assertTrue(json['error'])
            self.assertEqual(json['status'], 'invalid parameters')
        except requests.Timeout:
            self.fail('timeout')

    def test_user_does_not_exist(self):
        data = {
            'username': 'xXx_lol_i_am_so_random_XD_xXx',
            'password': '123'
        }
        try:
            r = requests.post('http://localhost:8000/api/auth/', json=data, timeout=60)
            json = r.json()
            self.assertTrue(json['error'])
            self.assertEqual(json['status'], 'user does not exist')
        except requests.Timeout:
            self.fail('timeout')

    def test_invalid_password(self):
        data = {
            'username': 'unittest',
            'password': '1234'
        }
        try:
            r = requests.post('http://localhost:8000/api/auth/', json=data, timeout=60)
            json = r.json()
            self.assertTrue(json['error'])
            self.assertEqual(json['status'], 'invalid password')
        except requests.Timeout:
            self.fail('timeout')

    def test_success(self):
        data = {
            'username': 'unittest',
            'password': '123'
        }
        try:
            r = requests.post('http://localhost:8000/api/auth/', json=data, timeout=60)
            json = r.json()
            self.assertFalse(json['error'])
            self.assertEqual(json['status'], 'success')
            self.assertEqual(json['token'], TOKEN)
        except requests.Timeout:
            self.fail('timeout')


class CompilersTests(TestCase):
    def test_compilers(self):
        r = requests.post('http://localhost:8000/api/compilers/', timeout=60)
        json = r.json()
        self.assertFalse(json['error'])
        self.assertEqual(json['compilers'], [c.name for c in settings.COMPILERS])


class PassesTests(TestCase):
    def test_passes(self):
        r = requests.post('http://localhost:8000/api/passes/', timeout=60)
        json = r.json()
        self.assertFalse(json['error'])
        self.assertEqual(json['passes'], [p.name for p in settings.OPS_PASSES])


class TasksTests(TestCase):
    def test_empty(self):
        data = {
            'token': TOKEN
        }
        try:
            r = requests.post('http://localhost:8000/api/tasks/', json=data, timeout=60)
            json = r.json()
            self.assertFalse(json['error'])
            self.assertEqual(json['status'], 'success')
            self.assertEqual(json['tasks'], [])
        except requests.Timeout:
            self.fail('timeout')
