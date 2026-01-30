from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthViewsTests(TestCase):
    def test_register_requires_first_and_last_name(self):
        url = reverse('register')
        res = self.client.post(
            url,
            data={
                'email': 'new@example.com',
                'password1': 'password123',
                'password2': 'password123',
                'first_name': '',
                'last_name': '',
            },
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertFalse(body['success'])
        self.assertTrue(any('First name' in e for e in body['errors']))
        self.assertTrue(any('Last name' in e for e in body['errors']))

    def test_register_success_creates_user_and_logs_in(self):
        url = reverse('register')
        res = self.client.post(
            url,
            data={
                'email': 'new@example.com',
                'password1': 'password123',
                'password2': 'password123',
                'first_name': 'New',
                'last_name': 'User',
            },
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertTrue(body['success'])
        self.assertTrue(body['user']['email'], 'new@example.com')
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

        # session endpoint reflects authenticated
        session_res = self.client.get(reverse('session'))
        self.assertEqual(session_res.status_code, 200)
        self.assertTrue(session_res.json()['authenticated'])

    def test_register_password_mismatch_and_short(self):
        url = reverse('register')
        # mismatch
        res = self.client.post(
            url,
            data={
                'email': 'a@example.com',
                'password1': 'password123',
                'password2': 'password12',
                'first_name': 'A',
                'last_name': 'B',
            },
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('Passwords do not match.', res.json()['errors'])

        # too short
        res2 = self.client.post(
            url,
            data={
                'email': 'b@example.com',
                'password1': 'short',
                'password2': 'short',
                'first_name': 'A',
                'last_name': 'B',
            },
            content_type='application/json',
        )
        self.assertEqual(res2.status_code, 400)
        self.assertTrue(any('at least 8' in e for e in res2.json()['errors']))

    def test_login_logout_flow(self):
        # Create user
        User.objects.create_user(
            email='login@example.com',
            password='password123',
            first_name='Log',
            last_name='In',
        )

        # Not authenticated initially
        self.assertFalse(self.client.get(reverse('session')).json()['authenticated'])

        # Login
        login_res = self.client.post(
            reverse('login'),
            data={'email': 'login@example.com', 'password': 'password123'},
            content_type='application/json',
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.json()['success'])

        # Session reflects auth
        self.assertTrue(self.client.get(reverse('session')).json()['authenticated'])

        # Logout
        logout_res = self.client.post(reverse('logout'))
        self.assertEqual(logout_res.status_code, 200)
        self.assertTrue(logout_res.json()['success'])

        # Session reflects unauthenticated
        self.assertFalse(self.client.get(reverse('session')).json()['authenticated'])
