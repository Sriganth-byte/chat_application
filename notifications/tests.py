from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()


class NotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='notifuser', email='notif@example.com', password='Pass123!'
        )
        res = self.client.post(reverse('login'), {
            'email': 'notif@example.com', 'password': 'Pass123!'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

        self.notif1 = Notification.objects.create(
            user=self.user, type='message',
            message='You have a new message', data={}
        )
        self.notif2 = Notification.objects.create(
            user=self.user, type='mention',
            message='You were mentioned', data={}, is_read=True
        )

    def test_list_all_notifications(self):
        res = self.client.get(reverse('notification-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_list_unread_only(self):
        res = self.client.get(reverse('notification-list') + '?unread=true')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertFalse(res.data[0]['is_read'])

    def test_unread_count(self):
        res = self.client.get(reverse('notification-unread-count'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['unread_count'], 1)

    def test_mark_single_read(self):
        res = self.client.post(
            reverse('mark-notification-read', kwargs={'notification_id': self.notif1.id})
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.notif1.refresh_from_db()
        self.assertTrue(self.notif1.is_read)

    def test_mark_all_read(self):
        res = self.client.post(reverse('mark-all-notifications-read'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['updated'], 1)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_cannot_mark_other_users_notification(self):
        other_user = User.objects.create_user(
            username='other', email='other@example.com', password='Pass123!'
        )
        other_notif = Notification.objects.create(
            user=other_user, type='message', message='Other notif', data={}
        )
        res = self.client.post(
            reverse('mark-notification-read', kwargs={'notification_id': other_notif.id})
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
