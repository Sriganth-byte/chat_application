from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from users.models import User

from .models import Room, Message, RoomMember
from .serializers import (
    RoomSerializer, RoomCreateSerializer, MessageSerializer, RoomMemberSerializer
)


# ─────────────────────────────────────────────
# Room endpoints
# ─────────────────────────────────────────────

class RoomListView(generics.ListCreateAPIView):
    """
    GET  /api/chat/rooms/        — list user's rooms
    POST /api/chat/rooms/        — create DM or group
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoomSerializer
    pagination_class = None  # return all user rooms; no page envelope

    def get_queryset(self):
        room_ids = RoomMember.objects.filter(
            user=self.request.user
        ).values_list('room_id', flat=True)
        return Room.objects.filter(id__in=room_ids).order_by('-created_at')

    def get_serializer_context(self):
        return {'request': self.request}

    def create(self, request, *args, **kwargs):
        serializer = RoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room_type = serializer.validated_data.get('type', 'group')
        
        if room_type == 'dm':
            # Create DM room using the manager method
            user_id = request.data.get('user_id')
            if not user_id and request.data.get('members'):
                user_id = request.data.get('members')[0]
            if not user_id:
                return Response(
                    {'error': 'user_id required for DM creation'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                other_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            room, _ = Room.objects.get_or_create_dm(request.user, other_user)
        else:
            # Create group room
            room = serializer.save(created_by=request.user)
            
            RoomMember.objects.create(
                room=room,
                user=request.user,
                role='admin' if room.type == 'group' else 'member'
            )
            
            for user_id in request.data.get('members', []):
                try:
                    user = User.objects.get(id=user_id)
                    RoomMember.objects.get_or_create(
                        room=room, user=user, defaults={'role': 'member'}
                    )
                except User.DoesNotExist:
                    continue

        return Response(
            RoomSerializer(room, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/chat/rooms/<id>/  — room details
    PATCH  /api/chat/rooms/<id>/  — update room (admin only)
    DELETE /api/chat/rooms/<id>/  — delete room (admin only)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoomSerializer
    queryset = Room.objects.all()

    def get_object(self):
        room = super().get_object()
        if not room.members.filter(user=self.request.user).exists():
            raise PermissionDenied('Not a member of this room')
        return room

    def update(self, request, *args, **kwargs):
        room = self.get_object()
        self._require_admin(room, request.user)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        self._require_admin(room, request.user)
        return super().destroy(request, *args, **kwargs)

    def _require_admin(self, room, user):
        membership = room.members.filter(user=user, role='admin').exists()
        if not membership:
            raise PermissionDenied('Only admins can perform this action')


# ─────────────────────────────────────────────
# Group member management
# ─────────────────────────────────────────────

class RoomMemberView(APIView):
    """
    POST   /api/chat/rooms/<id>/members/              — add member (admin only)
    DELETE /api/chat/rooms/<id>/members/<user_id>/    — remove member (admin only)
    PATCH  /api/chat/rooms/<id>/members/<user_id>/    — promote/demote (admin only)
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_room_as_admin(self, room_id, user):
        room = get_object_or_404(Room, id=room_id)
        if not room.members.filter(user=user, role='admin').exists():
            raise PermissionDenied('Only admins can manage members')
        return room

    def post(self, request, pk):
        room = self._get_room_as_admin(pk, request.user)
        if room.type != 'group':
            return Response(
                {'error': 'Cannot add members to a DM'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)

        from users.models import User
        user = get_object_or_404(User, id=user_id)
        membership, created = RoomMember.objects.get_or_create(
            room=room, user=user, defaults={'role': 'member'}
        )
        if not created:
            return Response({'error': 'User is already a member'}, status=status.HTTP_400_BAD_REQUEST)

        # Notify the added user
        from notifications.models import Notification
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        notification = Notification.objects.create(
            user=user,
            type='group_invite',
            message=f'{request.user.username} added you to {room.name}',
            data={'room_id': room.id}
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{user.id}_notifications',
            {
                'type': 'notification',
                'notification': {
                    'id': notification.id,
                    'type': notification.type,
                    'message': notification.message,
                    'data': notification.data,
                    'is_read': False,
                    'created_at': notification.created_at.isoformat(),
                }
            }
        )
        return Response(RoomMemberSerializer(membership).data, status=status.HTTP_201_CREATED)


class RoomMemberDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_room_as_admin(self, room_id, user):
        room = get_object_or_404(Room, id=room_id)
        if not room.members.filter(user=user, role='admin').exists():
            raise PermissionDenied('Only admins can manage members')
        return room

    def delete(self, request, pk, user_id):
        """Remove a member from the group."""
        room = self._get_room_as_admin(pk, request.user)
        # Prevent removing the last admin
        if str(user_id) == str(request.user.id):
            admin_count = room.members.filter(role='admin').count()
            if admin_count <= 1:
                return Response(
                    {'error': 'Cannot remove the last admin'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        membership = get_object_or_404(RoomMember, room=room, user_id=user_id)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, pk, user_id):
        """Promote or demote a member."""
        room = self._get_room_as_admin(pk, request.user)
        new_role = request.data.get('role')
        if new_role not in ('admin', 'member'):
            return Response({'error': 'role must be admin or member'}, status=status.HTTP_400_BAD_REQUEST)
        membership = get_object_or_404(RoomMember, room=room, user_id=user_id)
        membership.role = new_role
        membership.save(update_fields=['role'])
        return Response(RoomMemberSerializer(membership).data)


class LeaveRoomView(APIView):
    """
    POST /api/chat/rooms/<id>/leave/  — leave a group room
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        room = get_object_or_404(Room, id=pk)
        membership = get_object_or_404(RoomMember, room=room, user=request.user)

        # If last admin, block leave
        if membership.role == 'admin':
            admin_count = room.members.filter(role='admin').count()
            if admin_count <= 1:
                return Response(
                    {'error': 'Assign another admin before leaving'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        membership.delete()
        return Response({'message': 'Left room successfully'})


# ─────────────────────────────────────────────
# Message endpoints
# ─────────────────────────────────────────────

class MessageListView(generics.ListAPIView):
    """GET /api/chat/rooms/<room_id>/messages/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer
    pagination_class = None  # messages have their own [:100] limit; no page envelope

    def get_queryset(self):
        room = get_object_or_404(Room, id=self.kwargs['room_id'])
        if not room.members.filter(user=self.request.user).exists():
            raise PermissionDenied('Not a member of this room')
        return room.messages.select_related(
            'sender', 'reply_to__sender'
        ).order_by('-created_at')[:100]


class SendMessageView(APIView):
    """POST /api/chat/rooms/<room_id>/send/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)
        if not room.members.filter(user=request.user).exists():
            return Response({'error': 'Not a member of this room'}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get('content', '').strip()
        message_type = request.data.get('message_type', 'text')
        one_time = bool(request.data.get('one_time', False))
        if not content and message_type == 'text':
            return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(
            room=room, sender=request.user,
            message_type=message_type, content=content,
            one_time=one_time
        )
        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class MessageDetailView(APIView):
    """
    PUT    /api/chat/messages/<id>/  — edit (sender only)
    DELETE /api/chat/messages/<id>/  — delete (sender only)
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_owned_message(self, message_id, user):
        message = get_object_or_404(Message, id=message_id)
        if message.sender != user:
            raise PermissionDenied('Cannot modify another user\'s message')
        return message

    def put(self, request, message_id):
        message = self._get_owned_message(message_id, request.user)
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Content cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
        message.content = content
        message.edited = True
        message.edited_at = timezone.now()
        message.save(update_fields=['content', 'edited', 'edited_at'])
        return Response(MessageSerializer(message, context={'request': request}).data)

    def delete(self, request, message_id):
        message = self._get_owned_message(message_id, request.user)
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageConsumeView(APIView):
    """POST /api/chat/messages/<id>/consume/ — mark one-time media as consumed."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        if not message.room.members.filter(user=request.user).exists():
            return Response({'error': 'Not a member of this room'}, status=status.HTTP_403_FORBIDDEN)
        if not message.one_time:
            return Response({'error': 'Message is not one-time'}, status=status.HTTP_400_BAD_REQUEST)

        message.one_time_read_by.add(request.user)
        return Response(MessageSerializer(message, context={'request': request}).data)


# ─────────────────────────────────────────────
# Search endpoints
# ─────────────────────────────────────────────

class SearchView(APIView):
    """
    GET /api/chat/search/?q=<query>&type=<messages|rooms|users>

    Searches across messages (full-text), rooms, and users
    depending on the `type` param. Defaults to all three.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        search_type = request.query_params.get('type', 'all')

        if not q:
            return Response({'error': 'Query parameter q is required'}, status=status.HTTP_400_BAD_REQUEST)

        results = {}

        if search_type in ('all', 'messages'):
            results['messages'] = self._search_messages(q, request.user)

        if search_type in ('all', 'rooms'):
            results['rooms'] = self._search_rooms(q, request.user, request)

        if search_type in ('all', 'users'):
            results['users'] = self._search_users(q, request.user, request)

        return Response(results)

    def _search_messages(self, q, user):
        room_ids = RoomMember.objects.filter(
            user=user
        ).values_list('room_id', flat=True)

        # Use icontains so this works on both SQLite (dev) and PostgreSQL (prod)
        messages = (
            Message.objects
            .filter(room_id__in=room_ids, content__icontains=q)
            .order_by('-created_at')
            .select_related('sender', 'room')[:20]
        )
        return MessageSerializer(messages, many=True).data

    def _search_rooms(self, q, user, request):
        room_ids = RoomMember.objects.filter(
            user=user
        ).values_list('room_id', flat=True)

        rooms = Room.objects.filter(
            id__in=room_ids,
            type='group'
        ).filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        ).order_by('name')[:20]
        return RoomSerializer(rooms, many=True, context={'request': request}).data

    def _search_users(self, q, user, request):
        from users.models import User as UserModel
        from users.serializers import UserSerializer
        users = UserModel.objects.filter(
            Q(username__icontains=q) | Q(email__icontains=q)
        ).exclude(id=user.id)[:20]
        return UserSerializer(users, many=True, context={'request': request}).data


# ─────────────────────────────────────────────
# Message reaction endpoint
# ─────────────────────────────────────────────

class MessageReactionView(APIView):
    """
    POST /api/chat/messages/<id>/react/
    Toggle an emoji reaction on a message.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, message_id):
        from .models import MessageReaction
        message = get_object_or_404(Message, id=message_id)
        # Verify user is in the room
        if not message.room.members.filter(user=request.user).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)

        emoji = request.data.get('emoji', '').strip()
        if not emoji:
            return Response({'error': 'emoji required'}, status=status.HTTP_400_BAD_REQUEST)

        reaction, created = MessageReaction.objects.get_or_create(
            message=message, user=request.user, emoji=emoji
        )
        if not created:
            reaction.delete()
            created = False

        # Broadcast via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{message.room_id}',
            {
                'type': 'reaction.update',
                'message_id': message_id,
                'emoji': emoji,
                'user_id': request.user.id,
                'username': request.user.username,
                'added': created,
            }
        )

        # Return current reaction counts for this message
        from django.db.models import Count
        reaction_counts = (
            MessageReaction.objects.filter(message=message)
            .values('emoji')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        return Response({
            'added': created,
            'emoji': emoji,
            'reactions': list(reaction_counts)
        })
