from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from chat.models import Room, RoomMember, Message

User = get_user_model()


class ChatTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1', email='user1@example.com', password='Pass123!'
        )
        self.user2 = User.objects.create_user(
            username='user2', email='user2@example.com', password='Pass123!'
        )
        self.user3 = User.objects.create_user(
            username='user3', email='user3@example.com', password='Pass123!'
        )
        self._auth(self.user1)

    def _auth(self, user):
        res = self.client.post(reverse('login'), {
            'email': user.email, 'password': 'Pass123!'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def _create_group(self, name='Test Group', members=None):
        data = {'name': name, 'type': 'group', 'members': members or [self.user2.id]}
        return self.client.post(reverse('room-list'), data, format='json')

    def _create_dm(self):
        return self.client.post(reverse('room-list'), {
            'name': '', 'type': 'dm', 'members': [self.user2.id]
        }, format='json')


class RoomTests(ChatTestBase):
    def test_create_group_room(self):
        res = self._create_group()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['type'], 'group')

    def test_create_dm_room(self):
        res = self._create_dm()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['type'], 'dm')

    def test_list_rooms_only_own(self):
        self._create_group()
        self._auth(self.user3)
        res = self.client.get(reverse('room-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_room_detail_requires_membership(self):
        room_res = self._create_group()
        room_id = room_res.data['id']
        self._auth(self.user3)
        res = self.client.get(reverse('room-detail', kwargs={'pk': room_id}))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_room_admin_only(self):
        room_res = self._create_group()
        room_id = room_res.data['id']
        # user2 is member, not admin
        self._auth(self.user2)
        res = self.client.patch(
            reverse('room-detail', kwargs={'pk': room_id}),
            {'name': 'New Name'}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_room_as_admin(self):
        room_res = self._create_group()
        room_id = room_res.data['id']
        res = self.client.patch(
            reverse('room-detail', kwargs={'pk': room_id}),
            {'name': 'Updated Name'}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], 'Updated Name')


class GroupMemberTests(ChatTestBase):
    def setUp(self):
        super().setUp()
        res = self._create_group()
        self.room_id = res.data['id']

    def test_add_member(self):
        res = self.client.post(
            reverse('room-members', kwargs={'pk': self.room_id}),
            {'user_id': self.user3.id}
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(RoomMember.objects.filter(room_id=self.room_id, user=self.user3).exists())

    def test_add_duplicate_member(self):
        self.client.post(
            reverse('room-members', kwargs={'pk': self.room_id}),
            {'user_id': self.user3.id}
        )
        res = self.client.post(
            reverse('room-members', kwargs={'pk': self.room_id}),
            {'user_id': self.user3.id}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_member(self):
        res = self.client.delete(
            reverse('room-member-detail', kwargs={'pk': self.room_id, 'user_id': self.user2.id})
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RoomMember.objects.filter(room_id=self.room_id, user=self.user2).exists())

    def test_promote_member_to_admin(self):
        res = self.client.patch(
            reverse('room-member-detail', kwargs={'pk': self.room_id, 'user_id': self.user2.id}),
            {'role': 'admin'}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            RoomMember.objects.get(room_id=self.room_id, user=self.user2).role, 'admin'
        )

    def test_leave_room(self):
        self._auth(self.user2)
        res = self.client.post(reverse('room-leave', kwargs={'pk': self.room_id}))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(RoomMember.objects.filter(room_id=self.room_id, user=self.user2).exists())

    def test_last_admin_cannot_leave(self):
        res = self.client.post(reverse('room-leave', kwargs={'pk': self.room_id}))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_admin_cannot_add_member(self):
        self._auth(self.user2)
        res = self.client.post(
            reverse('room-members', kwargs={'pk': self.room_id}),
            {'user_id': self.user3.id}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MessageTests(ChatTestBase):
    def setUp(self):
        super().setUp()
        res = self._create_group()
        self.room_id = res.data['id']

    def test_send_message(self):
        res = self.client.post(
            reverse('send-message', kwargs={'room_id': self.room_id}),
            {'content': 'Hello!', 'message_type': 'text'}
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['content'], 'Hello!')

    def test_send_empty_text_message(self):
        res = self.client.post(
            reverse('send-message', kwargs={'room_id': self.room_id}),
            {'content': '', 'message_type': 'text'}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_messages(self):
        Message.objects.create(
            room_id=self.room_id, sender=self.user1,
            content='Test message', message_type='text'
        )
        res = self.client.get(
            reverse('message-list', kwargs={'room_id': self.room_id})
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

    def test_edit_own_message(self):
        msg = Message.objects.create(
            room_id=self.room_id, sender=self.user1,
            content='Original', message_type='text'
        )
        res = self.client.put(
            reverse('message-detail', kwargs={'message_id': msg.id}),
            {'content': 'Edited'}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['content'], 'Edited')
        self.assertTrue(res.data['edited'])

    def test_cannot_edit_others_message(self):
        msg = Message.objects.create(
            room_id=self.room_id, sender=self.user2,
            content='User2 message', message_type='text'
        )
        res = self.client.put(
            reverse('message-detail', kwargs={'message_id': msg.id}),
            {'content': 'Hacked'}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_own_message(self):
        msg = Message.objects.create(
            room_id=self.room_id, sender=self.user1,
            content='Delete me', message_type='text'
        )
        res = self.client.delete(
            reverse('message-detail', kwargs={'message_id': msg.id})
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Message.objects.filter(id=msg.id).exists())

    def test_cannot_delete_others_message(self):
        msg = Message.objects.create(
            room_id=self.room_id, sender=self.user2,
            content='User2 message', message_type='text'
        )
        res = self.client.delete(
            reverse('message-detail', kwargs={'message_id': msg.id})
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_cannot_send(self):
        self._auth(self.user3)
        res = self.client.post(
            reverse('send-message', kwargs={'room_id': self.room_id}),
            {'content': 'Intruder!', 'message_type': 'text'}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
