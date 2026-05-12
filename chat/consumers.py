import json
import asyncio
from datetime import timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache

User = get_user_model()

TYPING_TIMEOUT = 5  # seconds before server auto-clears typing indicator
HEARTBEAT_INTERVAL = 30  # seconds between ping/pong


class PresenceManager:
    """Manages user online/offline state in Redis and DB."""

    @staticmethod
    async def user_online(user_id, channel_name):
        session_key = f'presence:session:{user_id}:{channel_name}'
        await cache.aset(session_key, {'channel_name': channel_name}, timeout=3600)
        await cache.aset(f'presence:user:{user_id}', {
            'status': 'online',
            'last_seen': timezone.now().isoformat()
        }, timeout=3600)
        await PresenceManager._update_db(user_id, True)

    @staticmethod
    async def user_offline(user_id, channel_name):
        await cache.adelete(f'presence:session:{user_id}:{channel_name}')

        get_keys = database_sync_to_async(cache.keys)
        remaining = await get_keys(f'presence:session:{user_id}:*')

        if not remaining:
            now = timezone.now().isoformat()
            await cache.aset(f'presence:user:{user_id}', {
                'status': 'offline',
                'last_seen': now
            }, timeout=86400)
            await PresenceManager._update_db(user_id, False)

    @staticmethod
    @database_sync_to_async
    def _update_db(user_id, is_online):
        User.objects.filter(id=user_id).update(
            is_online=is_online,
            last_seen=timezone.now()
        )


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat.

    Handles:
      - message send / receive (with delivery receipt)
      - message edit broadcast
      - message delete broadcast
      - message reaction broadcast
      - typing indicators with server-side auto-timeout
      - message seen receipts + last_read update
      - heartbeat for connection health
      - chat history on connect
    """

    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close()
            return

        self.user = self.scope['user']
        self.user_id = str(self.user.id)
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self._typing_tasks = {}
        self._heartbeat_task = None

        if not await self.is_room_member(self.room_id, self.user_id):
            await self.close()
            return

        await PresenceManager.user_online(self.user_id, self.channel_name)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_add(
            f'user_{self.user_id}_notifications', self.channel_name
        )

        await self.accept()

        # Update last_read on connect so unread count resets
        await self.update_last_read()

        messages = await self.get_recent_messages(self.room_id)
        await self.send(text_data=json.dumps({
            'event': 'chat_history',
            'data': {'messages': messages}
        }))

        # Start heartbeat task
        self._heartbeat_task = asyncio.ensure_future(self._heartbeat_loop())

    async def disconnect(self, close_code):
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        # Cancel any pending typing timeouts
        for task in self._typing_tasks.values():
            task.cancel()

        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

        if hasattr(self, 'user_id'):
            await PresenceManager.user_offline(self.user_id, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        handlers = {
            'message': self.handle_message,
            'message_edit': self.handle_message_edit,
            'message_delete': self.handle_message_delete,
            'message_consume': self.handle_message_consume,
            'call_offer': self.handle_call_offer,
            'call_answer': self.handle_call_answer,
            'call_ice': self.handle_call_ice,
            'call_end': self.handle_call_end,
            'call_decline': self.handle_call_decline,
            'typing_start': self.handle_typing_start,
            'typing_stop': self.handle_typing_stop,
            'message_seen': self.handle_message_seen,
            'reaction': self.handle_reaction,
            'ping': self.handle_ping,
            'pong': self.handle_pong,
        }
        handler = handlers.get(data.get('type'))
        if handler:
            await handler(data)

    async def _heartbeat_loop(self):
        """Send periodic pings to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await self.send(text_data=json.dumps({
                    'event': 'ping',
                    'data': {'timestamp': timezone.now().isoformat()}
                }))
        except asyncio.CancelledError:
            pass

    async def handle_ping(self, data):
        """Handle ping from client."""
        await self.send(text_data=json.dumps({
            'event': 'pong',
            'data': {'timestamp': timezone.now().isoformat()}
        }))

    async def handle_pong(self, data):
        """Client heartbeat response. Kept for protocol compatibility."""
        return

    async def handle_reaction(self, data):
        """Handle message reaction from client."""
        message_id = data.get('message_id')
        emoji = data.get('emoji', '').strip()

        if not message_id or not emoji:
            return

        try:
            # Toggle reaction
            reaction, created = await self.toggle_reaction(
                message_id, self.user_id, emoji
            )

            # Broadcast to room
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'reaction.update',
                'message_id': message_id,
                'emoji': emoji,
                'user_id': self.user_id,
                'username': self.user.username,
                'added': created,
            })
        except Exception as e:
            await self.send(text_data=json.dumps({
                'event': 'error',
                'data': {'message': f'Failed to react: {str(e)}'}
            }))

    # ------------------------------------------------------------------ #
    # Incoming event handlers
    # ------------------------------------------------------------------ #

    async def handle_message(self, data):
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        reply_to_id = data.get('reply_to_id')
        file_name = data.get('file_name')

        if not content and message_type == 'text':
            return

        try:
            one_time = bool(data.get('one_time', False))
            message = await self.save_message(
                self.room_id, self.user_id, content, message_type, reply_to_id,
                one_time, file_name
            )
            message_data = await self.serialize_message(message)

            # Broadcast to all OTHER members (sender gets their own message via message_sent)
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'message.broadcast',
                'message': message_data,
                'sender_channel': self.channel_name,
            })

            # Delivery receipt to sender
            await self.send(text_data=json.dumps({
                'event': 'message_sent',
                'data': message_data
            }))

            # Notify offline members — in a separate task so failures don't affect message delivery
            asyncio.ensure_future(self._notify_offline_members_async(self.room_id, message_data))
        except Exception as e:
            import logging
            logging.getLogger('chat').exception('handle_message failed: %s', e)
            await self.send(text_data=json.dumps({
                'event': 'error',
                'data': {'message': 'Failed to send message'}
            }))

    async def handle_message_edit(self, data):
        message_id = data.get('message_id')
        content = data.get('content', '').strip()
        if not message_id or not content:
            return

        updated = await self.edit_message(message_id, content)
        if not updated:
            await self.send(text_data=json.dumps({
                'event': 'error',
                'data': {'message': 'Unable to edit message'}
            }))
            return

        message_data = await self.serialize_message_by_id(message_id)
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'message.edited',
            'message': message_data,
        })

    async def handle_message_delete(self, data):
        message_id = data.get('message_id')
        if not message_id:
            return

        deleted = await self.delete_message(message_id)
        if not deleted:
            await self.send(text_data=json.dumps({
                'event': 'error',
                'data': {'message': 'Unable to delete message'}
            }))
            return

        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'message.deleted',
            'message_id': message_id,
            'room_id': self.room_id,
        })

    async def handle_message_consume(self, data):
        message_id = data.get('message_id')
        if not message_id:
            return
        await self.mark_one_time_consumed(message_id)
        message_data = await self.serialize_message_by_id(message_id)
        await self.send(text_data=json.dumps({
            'event': 'message_consumed',
            'data': message_data,
        }))

    async def handle_call_offer(self, data):
        """Handle WebRTC call offer."""
        offer = data.get('offer')
        call_type = data.get('call_type', 'voice')
        if not offer:
            return

        member_ids = await self.get_room_member_ids(self.room_id)
        
        # Broadcast offer to all other room members
        event = {
            'type': 'call.offer',
            'room_id': self.room_id,
            'offer': offer,
            'call_type': call_type,
            'from_user': self.user_id,
            'from_username': self.user.username,
            'sender_channel': self.channel_name,
        }
        await self.channel_layer.group_send(self.room_group_name, event)

        for member_id in member_ids:
            if str(member_id) == str(self.user_id):
                continue
            notification_payload = await self.create_call_notification(
                member_id=member_id,
                room_id=self.room_id,
                offer=offer,
                call_type=call_type,
            )
            await self.channel_layer.group_send(
                f'user_{member_id}_notifications',
                {
                    'type': 'notification',
                    'notification': notification_payload,
                }
            )
            await self.channel_layer.group_send(
                f'user_{member_id}_notifications',
                {**event, 'type': 'call.offer.notification'}
            )

    async def handle_call_answer(self, data):
        """Handle WebRTC call answer."""
        answer = data.get('answer')
        target_user = data.get('target_user')
        if not answer or not target_user:
            return
        
        # Send answer to specific user
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'call.answer',
            'room_id': self.room_id,
            'answer': answer,
            'target_user': target_user,
            'from_user': self.user_id,
            'sender_channel': self.channel_name,
        })

    async def handle_call_ice(self, data):
        """Handle ICE candidate exchange."""
        candidate = data.get('candidate')
        target_user = data.get('target_user')  # may be None — broadcast to all non-senders
        if not candidate:
            return

        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'call.ice',
            'room_id': self.room_id,
            'candidate': candidate,
            'target_user': target_user,  # None means send to all non-senders
            'from_user': self.user_id,
            'sender_channel': self.channel_name,
        })

    async def handle_call_end(self, data):
        """Handle call end."""
        member_ids = await self.get_room_member_ids(self.room_id)
        event = {
            'type': 'call.end',
            'room_id': self.room_id,
            'from_user': self.user_id,
            'sender_channel': self.channel_name,
        }
        await self.channel_layer.group_send(self.room_group_name, event)

        for member_id in member_ids:
            if str(member_id) == str(self.user_id):
                continue
            await self.channel_layer.group_send(
                f'user_{member_id}_notifications',
                {**event, 'type': 'call.end.notification'}
            )

    async def handle_call_decline(self, data):
        """Handle call decline."""
        target_user = data.get('target_user')
        member_ids = await self.get_room_member_ids(self.room_id)
        room_type = await self.get_room_type(self.room_id)
        event = {
            'type': 'call.declined',
            'room_id': self.room_id,
            'from_user': self.user_id,
            'target_user': target_user if room_type == 'dm' else None,
            'sender_channel': self.channel_name,
        }
        await self.channel_layer.group_send(self.room_group_name, event)

        for member_id in member_ids:
            if str(member_id) == str(self.user_id):
                continue
            await self.channel_layer.group_send(
                f'user_{member_id}_notifications',
                {**event, 'type': 'call.declined.notification'}
            )

    async def handle_typing_start(self, data):
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'typing.start',
            'user_id': self.user_id,
            'username': self.user.username,
            'sender_channel': self.channel_name,
        })
        existing = self._typing_tasks.pop(self.user_id, None)
        if existing:
            existing.cancel()
        self._typing_tasks[self.user_id] = asyncio.ensure_future(
            self._auto_clear_typing(self.user_id)
        )

    async def handle_typing_stop(self, data):
        task = self._typing_tasks.pop(self.user_id, None)
        if task:
            task.cancel()
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'typing.stop',
            'user_id': self.user_id,
            'sender_channel': self.channel_name,
        })

    async def handle_message_seen(self, data):
        message_ids = data.get('message_ids') or []
        if not isinstance(message_ids, list):
            message_ids = [message_ids]
        message_ids = [mid for mid in message_ids if mid]
        if not message_ids:
            return
        await self.mark_messages_seen(message_ids)
        await self.update_last_read()
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'message.seen',
            'user_id': self.user_id,
            'message_ids': message_ids,
        })

    async def _auto_clear_typing(self, user_id):
        try:
            await asyncio.sleep(TYPING_TIMEOUT)
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'typing.stop',
                'user_id': user_id,
                'sender_channel': self.channel_name,
            })
            self._typing_tasks.pop(user_id, None)
        except asyncio.CancelledError:
            pass

    # ... rest of the consumer remains the same ...

    # ------------------------------------------------------------------ #
    # Channel layer event handlers (group_send → WebSocket client)
    # ------------------------------------------------------------------ #

    async def message_broadcast(self, event):
        # Skip sending back to the sender — they already received message_sent
        if event.get('sender_channel') == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'event': 'message_received',
            'data': event['message']
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'event': 'message_edited',
            'data': event['message']
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'event': 'message_deleted',
            'data': {
                'message_id': event['message_id'],
                'room_id': event['room_id'],
            }
        }))

    async def reaction_update(self, event):
        """Send reaction update to client."""
        await self.send(text_data=json.dumps({
            'event': 'reaction_update',
            'data': {
                'message_id': event['message_id'],
                'emoji': event['emoji'],
                'user_id': event['user_id'],
                'username': event['username'],
                'added': event['added'],
            }
        }))

    async def typing_start(self, event):
        if event.get('sender_channel') == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'event': 'typing_start',
            'data': {'user_id': event['user_id'], 'username': event['username']}
        }))

    async def typing_stop(self, event):
        if event.get('sender_channel') == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'event': 'typing_stop',
            'data': {'user_id': event['user_id']}
        }))

    async def message_seen(self, event):
        await self.send(text_data=json.dumps({
            'event': 'message_seen',
            'data': {'user_id': event['user_id'], 'message_ids': event['message_ids']}
        }))

    async def call_offer(self, event):
        """Send call offer to client."""
        if event.get('sender_channel') == self.channel_name:
            return
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

    async def call_answer(self, event):
        """Send call answer to client."""
        if event.get('sender_channel') == self.channel_name:
            return
        # Only send to the target user
        if str(event['target_user']) == str(self.user_id):
            await self.send(text_data=json.dumps({
                'event': 'call_answer',
                'data': {
                    'room_id': event['room_id'],
                    'answer': event['answer'],
                    'from_user': event['from_user'],
                }
            }))

    async def call_ice(self, event):
        """Send ICE candidate to client."""
        if event.get('sender_channel') == self.channel_name:
            return
        # If target_user is set, only send to that user; otherwise broadcast to all non-senders
        target_user = event.get('target_user')
        if target_user and str(target_user) != str(self.user_id):
            return
        await self.send(text_data=json.dumps({
            'event': 'call_ice',
            'data': {
                'room_id': event['room_id'],
                'candidate': event['candidate'],
                'from_user': event['from_user'],
            }
        }))

    async def call_end(self, event):
        """Send call end to client."""
        if event.get('sender_channel') == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'event': 'call_end',
            'data': {
                'room_id': event['room_id'],
                'from_user': event['from_user'],
            }
        }))

    async def call_declined(self, event):
        """Send call declined to client."""
        if event.get('sender_channel') == self.channel_name:
            return
        if not event.get('target_user') or str(event['target_user']) == str(self.user_id):
            await self.send(text_data=json.dumps({
                'event': 'call_declined',
                'data': {
                    'room_id': event['room_id'],
                    'from_user': event['from_user'],
                }
            }))

    async def call_offer_notification(self, event):
        """Chat sockets ignore global call notifications; the notification socket owns the ringing UI."""
        return

    async def call_end_notification(self, event):
        """Chat sockets receive call endings through the room group."""
        return

    async def call_declined_notification(self, event):
        """Chat sockets receive declines through the room group."""
        return

    # ------------------------------------------------------------------ #
    # DB helpers
    # ------------------------------------------------------------------ #

    @database_sync_to_async
    def is_room_member(self, room_id, user_id):
        from chat.models import RoomMember
        return RoomMember.objects.filter(room_id=room_id, user_id=user_id).exists()

    @database_sync_to_async
    def get_room_member_ids(self, room_id):
        from chat.models import RoomMember
        return list(RoomMember.objects.filter(room_id=room_id).values_list('user_id', flat=True))

    @database_sync_to_async
    def get_room_type(self, room_id):
        from chat.models import Room
        return Room.objects.filter(id=room_id).values_list('type', flat=True).first()

    @database_sync_to_async
    def create_call_notification(self, member_id, room_id, offer, call_type):
        from notifications.models import Notification

        notification = Notification.objects.create(
            user_id=member_id,
            type='system',
            message=f'{self.user.username} is calling you',
            data={
                'event': 'call_offer',
                'room_id': room_id,
                'offer': offer,
                'call_type': call_type,
                'from_user': self.user_id,
                'from_username': self.user.username,
            }
        )
        return {
            'id': notification.id,
            'type': notification.type,
            'message': notification.message,
            'data': notification.data,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
        }

    @database_sync_to_async
    def update_last_read(self):
        from chat.models import RoomMember
        RoomMember.objects.filter(
            room_id=self.room_id, user_id=self.user_id
        ).update(last_read=timezone.now())

    @database_sync_to_async
    def get_recent_messages(self, room_id, limit=50):
        from chat.models import Message
        from chat.serializers import MessageSerializer
        from rest_framework.renderers import JSONRenderer
        import json
        messages = Message.objects.filter(
            room_id=room_id
        ).select_related('sender', 'reply_to__sender').order_by('-created_at')[:limit]
        data = MessageSerializer(messages, many=True, context={'user_id': int(self.user_id)}).data
        return json.loads(JSONRenderer().render(data))

    @database_sync_to_async
    def save_message(self, room_id, sender_id, content, message_type, reply_to_id=None, one_time=False, file_name=None):
        from chat.models import Message, Room
        message = Message.objects.create(
            room=Room.objects.get(id=room_id),
            sender=User.objects.get(id=sender_id),
            content=content,
            message_type=message_type,
            reply_to_id=reply_to_id,
            one_time=one_time,
            file_name=file_name or '',
        )
        # Refresh with all relations so serialize_message works without lazy hits
        return Message.objects.select_related(
            'sender', 'reply_to__sender'
        ).get(id=message.id)

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        """Edit message — only the sender can edit within the allowed window."""
        from chat.models import Message
        cutoff = timezone.now() - timedelta(minutes=15)
        updated = Message.objects.filter(
            id=message_id,
            sender_id=self.user_id,
            room_id=self.room_id,
            created_at__gte=cutoff
        ).update(content=new_content, edited=True, edited_at=timezone.now())
        return updated > 0

    @database_sync_to_async
    def delete_message(self, message_id):
        """Delete message — only the sender can delete within the allowed window."""
        from chat.models import Message
        cutoff = timezone.now() - timedelta(minutes=15)
        deleted, _ = Message.objects.filter(
            id=message_id,
            sender_id=self.user_id,
            room_id=self.room_id,
            created_at__gte=cutoff
        ).delete()
        return deleted > 0

    @database_sync_to_async
    def toggle_reaction(self, message_id, user_id, emoji):
        """Toggle reaction on a message. Returns (reaction, created)."""
        from chat.models import MessageReaction, Message
        message = Message.objects.get(id=message_id, room_id=self.room_id)
        reaction, created = MessageReaction.objects.get_or_create(
            message=message, user_id=user_id, emoji=emoji
        )
        if not created:
            reaction.delete()
            return None, False
        return reaction, True

    @database_sync_to_async
    def serialize_message(self, message):
        from chat.serializers import MessageSerializer
        from rest_framework.renderers import JSONRenderer
        import json
        data = MessageSerializer(message, context={'user_id': int(self.user_id)}).data
        return json.loads(JSONRenderer().render(data))

    @database_sync_to_async
    def serialize_message_by_id(self, message_id):
        from chat.models import Message
        from chat.serializers import MessageSerializer
        from rest_framework.renderers import JSONRenderer
        import json
        message = Message.objects.select_related(
            'sender', 'reply_to__sender'
        ).get(id=message_id)
        data = MessageSerializer(message, context={'user_id': int(self.user_id)}).data
        return json.loads(JSONRenderer().render(data))

    @database_sync_to_async
    def mark_messages_seen(self, message_ids):
        from chat.models import Message
        user = User.objects.get(id=self.user_id)
        for message in Message.objects.filter(id__in=message_ids):
            message.seen_by.add(user)
        Message.objects.filter(id__in=message_ids).update(is_seen=True)

    @database_sync_to_async
    def mark_one_time_consumed(self, message_id):
        from chat.models import Message
        user = User.objects.get(id=self.user_id)
        message = Message.objects.get(id=message_id, room_id=self.room_id)
        message.one_time_read_by.add(user)
        return message

    @database_sync_to_async
    def _notify_offline_members_async(self, room_id, message_data):
        from chat.models import RoomMember
        from notifications.models import Notification
        member_ids = RoomMember.objects.filter(room_id=room_id).exclude(
            user_id=self.user_id
        ).values_list('user_id', flat=True)
        notifications = [
            Notification(
                user_id=user_id,
                type='message',
                message=f'{self.user.username}: {message_data.get("content", "New message")[:120]}',
                data={'room_id': room_id, 'message_id': message_data.get('id')},
            )
            for user_id in member_ids
        ]
        if notifications:
            Notification.objects.bulk_create(notifications)
