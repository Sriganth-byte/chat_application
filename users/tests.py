from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.profile_url = reverse('profile')
        self.refresh_url = reverse('token_refresh')

    def _register(self, username='testuser', email='test@example.com', password='StrongPass123!'):
        return self.client.post(self.register_url, {
            'username': username,
            'email': email,
            'password': password,
            'password2': password,
        })

    def _login(self, email='test@example.com', password='StrongPass123!'):
        return self.client.post(self.login_url, {
            'email': email,
            'password': password,
        })

    def test_register_success(self):
        res = self._register()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['username'], 'testuser')
        self.assertEqual(res.data['email'], 'test@example.com')

    def test_register_duplicate_email(self):
        self._register()
        res = self._register(username='other')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        res = self.client.post(self.register_url, {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'StrongPass123!',
            'password2': 'WrongPass123!',
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        self._register()
        res = self._login()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_login_wrong_password(self):
        self._register()
        res = self._login(password='WrongPass!')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_requires_auth(self):
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get(self):
        self._register()
        login_res = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['access']}")
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'testuser')

    def test_profile_update(self):
        self._register()
        login_res = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['access']}")
        res = self.client.put(self.profile_url, {'bio': 'Hello world'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['bio'], 'Hello world')

    def test_logout_blacklists_token(self):
        self._register()
        login_res = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['access']}")
        res = self.client.post(self.logout_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_token_refresh(self):
        self._register()
        login_res = self._login()
        res = self.client.post(self.refresh_url, {'refresh': login_res.data['refresh']})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)

    def test_user_list_search(self):
        self._register()
        User.objects.create_user(username='alice', email='alice@example.com', password='Pass123!')
        login_res = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['access']}")
        res = self.client.get(reverse('user-list') + '?q=alice')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['username'], 'alice')
