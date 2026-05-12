from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.db import transaction

from .models import FriendRequest, Friendship, Follow, UserProfile
from .serializers import FriendRequestSerializer, FriendshipSerializer, UserProfileSerializer
from users.models import User
from users.serializers import UserSerializer
from notifications.models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def _send_notification(user, notif_type, message, data):
    """Helper to create and broadcast a notification."""
    notification = Notification.objects.create(
        user=user, type=notif_type, message=message, data=data
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


class UserProfileView(APIView):
    """GET /api/social/profile/<username>/ — public profile"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, username):
        if request.user.username != username:
            return Response({'error': 'Cannot edit another user\'s profile'}, status=403)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class FriendRequestView(APIView):
    """POST /api/social/friend-request/ — send request"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        receiver_id = request.data.get('user_id')
        if not receiver_id:
            return Response({'error': 'user_id required'}, status=400)
        receiver = get_object_or_404(User, id=receiver_id)

        if receiver == request.user:
            return Response({'error': 'Cannot send friend request to yourself'}, status=400)

        if Friendship.are_friends(request.user, receiver):
            return Response({'error': 'Already friends'}, status=400)

        if request.user.blocked_users.filter(id=receiver.id).exists():
            return Response({'error': 'Cannot send request'}, status=400)

        existing = FriendRequest.objects.filter(
            Q(sender=request.user, receiver=receiver) |
            Q(sender=receiver, receiver=request.user),
            status='pending'
        ).first()
        if existing:
            direction = 'sent' if existing.sender == request.user else 'received'
            return Response({
                'error': 'Friend request already pending',
                'direction': direction,
                'request_id': existing.id,
                'request': FriendRequestSerializer(existing).data,
            }, status=400)

        req = FriendRequest.objects.create(sender=request.user, receiver=receiver)
        _send_notification(
            receiver, 'friend_request',
            f'{request.user.username} sent you a friend request',
            {'request_id': req.id, 'sender_id': request.user.id, 'sender_username': request.user.username}
        )
        return Response(FriendRequestSerializer(req).data, status=201)


class FriendRequestActionView(APIView):
    """PATCH /api/social/friend-request/<id>/ — accept/reject/withdraw"""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        action = request.data.get('action')  # accept | reject | withdraw
        req = get_object_or_404(FriendRequest, id=pk)

        if action == 'withdraw':
            if req.sender != request.user:
                return Response({'error': 'Not your request'}, status=403)
            req.status = 'withdrawn'
            req.save()
            return Response({'message': 'Request withdrawn'})

        if req.receiver != request.user:
            return Response({'error': 'Not your request'}, status=403)

        if req.status != 'pending':
            return Response({'error': 'Request is no longer pending'}, status=400)

        if action == 'accept':
            with transaction.atomic():
                req.status = 'accepted'
                req.save()
                u1, u2 = (req.sender, req.receiver) if req.sender.id < req.receiver.id else (req.receiver, req.sender)
                Friendship.objects.get_or_create(user1=u1, user2=u2)
            _send_notification(
                req.sender, 'friend_accepted',
                f'{request.user.username} accepted your friend request',
                {'user_id': request.user.id, 'username': request.user.username}
            )
            return Response({'message': 'Friend request accepted'})

        elif action == 'reject':
            req.status = 'rejected'
            req.save()
            return Response({'message': 'Request rejected'})

        return Response({'error': 'Invalid action'}, status=400)


class FriendListView(generics.ListAPIView):
    """GET /api/social/friends/ — list friends"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        return Friendship.get_friends(self.request.user)


class FriendRequestListView(generics.ListAPIView):
    """GET /api/social/friend-requests/?direction=received|sent"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FriendRequestSerializer

    def get_queryset(self):
        direction = self.request.query_params.get('direction', 'received')
        if direction == 'sent':
            return FriendRequest.objects.filter(sender=self.request.user, status='pending')
        return FriendRequest.objects.filter(receiver=self.request.user, status='pending')


class UnfriendView(APIView):
    """DELETE /api/social/friends/<user_id>/"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, user_id):
        other = get_object_or_404(User, id=user_id)
        u1, u2 = (request.user, other) if request.user.id < other.id else (other, request.user)
        Friendship.objects.filter(user1=u1, user2=u2).delete()
        return Response({'message': 'Unfriended'}, status=204)


class FollowView(APIView):
    """POST /api/social/follow/<user_id>/ — follow/unfollow toggle"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        target = get_object_or_404(User, id=user_id)
        if target == request.user:
            return Response({'error': 'Cannot follow yourself'}, status=400)

        follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
        if not created:
            follow.delete()
            return Response({'following': False})

        _send_notification(
            target, 'new_follower',
            f'{request.user.username} started following you',
            {'user_id': request.user.id, 'username': request.user.username}
        )
        return Response({'following': True})


class UserSuggestionsView(APIView):
    """GET /api/social/suggestions/ — people you may know"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        friend_ids = set(Friendship.get_friends(user).values_list('id', flat=True))
        blocked_ids = set(user.blocked_users.values_list('id', flat=True))

        # Also exclude users with pending requests in either direction
        pending_sent = set(FriendRequest.objects.filter(
            sender=user, status='pending'
        ).values_list('receiver_id', flat=True))
        pending_received = set(FriendRequest.objects.filter(
            receiver=user, status='pending'
        ).values_list('sender_id', flat=True))

        exclude_ids = friend_ids | blocked_ids | pending_sent | pending_received | {user.id}

        # Friends of friends first
        fof_ids = set()
        for fid in list(friend_ids)[:20]:  # cap to avoid slow queries
            fof_ids |= set(Friendship.get_friends(
                User.objects.get(id=fid)
            ).values_list('id', flat=True))
        fof_ids -= exclude_ids

        suggestions = list(User.objects.filter(id__in=fof_ids)[:10])
        if len(suggestions) < 10:
            more = User.objects.exclude(
                id__in=exclude_ids
            ).order_by('-date_joined')[:(10 - len(suggestions))]
            suggestions = suggestions + list(more)

        return Response(UserSerializer(suggestions[:10], many=True, context={'request': request}).data)
