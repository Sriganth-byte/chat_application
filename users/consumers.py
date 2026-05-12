import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class PresenceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user presence.
    Connects to ws/presence/ and receives user_online / user_offline
    events for all room-mates of the authenticated user.
    """

    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close()
            return

        self.user = self.scope['user']
        self.user_id = str(self.user.id)
        self.presence_group = f'presence_user_{self.user_id}'

        # Join own presence group so others can push events to this user
        await self.channel_layer.group_add(self.presence_group, self.channel_name)

        # Join presence groups of every room-mate so we receive their events
        self.roommate_groups = await self.get_roommate_presence_groups()
        for group in self.roommate_groups:
            await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()

        # Immediately push current online status of all room-mates
        online_statuses = await self.get_roommate_statuses()
        await self.send(text_data=json.dumps({
            'event': 'presence_snapshot',
            'data': online_statuses
        }))

        # Broadcast this user coming online to all their room-mates
        await self.broadcast_to_roommates('user_online')

    async def disconnect(self, close_code):
        if not hasattr(self, 'user_id'):
            return

        # Broadcast this user going offline
        await self.broadcast_to_roommates('user_offline')

        # Leave all groups
        await self.channel_layer.group_discard(self.presence_group, self.channel_name)
        for group in getattr(self, 'roommate_groups', []):
            await self.channel_layer.group_discard(group, self.channel_name)

        # Persist offline status to DB
        await self.set_user_offline()

    async def broadcast_to_roommates(self, event_type):
        """Send online/offline event to all room-mates' presence groups."""
        roommate_ids = await self.get_roommate_ids()
        payload = {
            'type': 'presence.update',
            'event': event_type,
            'user_id': self.user_id,
            'username': self.user.username,
            'timestamp': timezone.now().isoformat(),
        }
        for uid in roommate_ids:
            await self.channel_layer.group_send(f'presence_user_{uid}', payload)

    # ------------------------------------------------------------------ #
    # Channel layer event handlers (server → this WebSocket client)
    # ------------------------------------------------------------------ #

    async def presence_update(self, event):
        """Forward presence update to the connected client."""
        await self.send(text_data=json.dumps({
            'event': event['event'],          # 'user_online' or 'user_offline'
            'data': {
                'user_id': event['user_id'],
                'username': event['username'],
                'timestamp': event['timestamp'],
            }
        }))

    # ------------------------------------------------------------------ #
    # DB helpers
    # ------------------------------------------------------------------ #

    @database_sync_to_async
    def get_roommate_ids(self):
        """Return IDs of all users who share at least one room with this user."""
        from chat.models import RoomMember
        room_ids = RoomMember.objects.filter(
            user=self.user
        ).values_list('room_id', flat=True)

        return list(
            RoomMember.objects.filter(room_id__in=room_ids)
            .exclude(user=self.user)
            .values_list('user_id', flat=True)
            .distinct()
        )

    @database_sync_to_async
    def get_roommate_presence_groups(self):
        """Return channel group names for all room-mates."""
        from chat.models import RoomMember
        room_ids = RoomMember.objects.filter(
            user=self.user
        ).values_list('room_id', flat=True)

        ids = list(
            RoomMember.objects.filter(room_id__in=room_ids)
            .exclude(user=self.user)
            .values_list('user_id', flat=True)
            .distinct()
        )
        return [f'presence_user_{uid}' for uid in ids]

    @database_sync_to_async
    def get_roommate_statuses(self):
        """Return {user_id: {is_online, last_seen}} for all room-mates."""
        from django.contrib.auth import get_user_model
        from chat.models import RoomMember
        User = get_user_model()

        room_ids = RoomMember.objects.filter(
            user=self.user
        ).values_list('room_id', flat=True)

        roommate_ids = list(
            RoomMember.objects.filter(room_id__in=room_ids)
            .exclude(user=self.user)
            .values_list('user_id', flat=True)
            .distinct()
        )

        users = User.objects.filter(id__in=roommate_ids).values(
            'id', 'username', 'is_online', 'last_seen'
        )
        return [
            {
                'user_id': str(u['id']),
                'username': u['username'],
                'is_online': u['is_online'],
                'last_seen': u['last_seen'].isoformat() if u['last_seen'] else None,
            }
            for u in users
        ]

    @database_sync_to_async
    def set_user_offline(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.filter(id=self.user.id).update(
            is_online=False,
            last_seen=timezone.now()
        )
