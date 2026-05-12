import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    """
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.user = self.scope["user"]
        self.user_id = str(self.user.id)
        self.group_name = f"user_{self.user_id}_notifications"

        # Join user's notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'mark_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)
            elif message_type == 'mark_all_read':
                await self.mark_all_notifications_read()
            elif message_type == 'call_decline':
                await self.forward_call_decline(data)
        except json.JSONDecodeError:
            pass

    async def notification(self, event):
        """Send notification to client"""
        await self.send(text_data=json.dumps({
            'event': 'notification',
            'data': event.get('notification', {})
        }))

    async def call_offer_notification(self, event):
        """Send incoming call offer to clients that are not in the chat room."""
        await self.send(text_data=json.dumps({
            'event': 'call_offer',
            'data': {
                'room_id': event['room_id'],
                'offer': event['offer'],
                'call_type': event['call_type'],
                'from_user': event['from_user'],
                'from_username': event['from_username'],
            }
        }))

    async def call_end_notification(self, event):
        """Tell every open client that a call ended."""
        await self.send(text_data=json.dumps({
            'event': 'call_end',
            'data': {
                'room_id': event['room_id'],
                'from_user': event['from_user'],
            }
        }))

    async def call_declined_notification(self, event):
        """Tell every open client that a call was declined."""
        await self.send(text_data=json.dumps({
            'event': 'call_declined',
            'data': {
                'room_id': event['room_id'],
                'from_user': event['from_user'],
            }
        }))

    async def forward_call_decline(self, data):
        """Allow users to decline a ringing call without opening the chat room."""
        room_id = data.get('room_id')
        target_user = data.get('target_user')
        if not room_id or not await self.is_room_member(room_id):
            return
        room_type = await self.get_room_type(room_id)

        event = {
            'type': 'call.declined',
            'room_id': room_id,
            'from_user': self.user_id,
            'target_user': target_user if room_type == 'dm' else None,
            'sender_channel': self.channel_name,
        }
        await self.channel_layer.group_send(f'chat_{room_id}', event)

        member_ids = await self.get_room_member_ids(room_id)
        for member_id in member_ids:
            if str(member_id) == str(self.user_id):
                continue
            await self.channel_layer.group_send(
                f'user_{member_id}_notifications',
                {**event, 'type': 'call.declined.notification'}
            )

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark single notification as read"""
        from notifications.models import Notification
        from django.shortcuts import get_object_or_404

        notification = Notification.objects.filter(
            id=notification_id,
            user=self.user
        ).first()

        if notification:
            notification.is_read = True
            notification.save()

    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Mark all notifications as read"""
        from notifications.models import Notification
        Notification.objects.filter(
            user=self.user,
            is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def is_room_member(self, room_id):
        from chat.models import RoomMember
        return RoomMember.objects.filter(room_id=room_id, user=self.user).exists()

    @database_sync_to_async
    def get_room_member_ids(self, room_id):
        from chat.models import RoomMember
        return list(RoomMember.objects.filter(room_id=room_id).values_list('user_id', flat=True))

    @database_sync_to_async
    def get_room_type(self, room_id):
        from chat.models import Room
        return Room.objects.filter(id=room_id).values_list('type', flat=True).first()
