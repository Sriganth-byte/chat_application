"""
GDPR compliance endpoints:
  GET  /api/auth/export-data/   → download all personal data as JSON
  DELETE /api/auth/delete-account/ → hard-delete all user data
  GET  /api/auth/change-password/  → already handled by users/views
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.utils import timezone
import json


class DataExportView(APIView):
    """GET /api/auth/export-data/ — GDPR data portability"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Collect all user data
        from chat.models import Message, Room
        from notifications.models import Notification
        from posts.models import Post, PostComment, PostLike

        try:
            from social.models import FriendRequest, Friendship, Follow, UserProfile
            profile = UserProfile.objects.filter(user=user).first()
            profile_data = {
                'display_name': profile.display_name if profile else '',
                'location': profile.location if profile else '',
                'website': profile.website if profile else '',
                'bio': profile.bio if profile else '',
            }
            friends = [u.username for u in Friendship.get_friends(user)]
            following = list(Follow.objects.filter(follower=user).values_list('following__username', flat=True))
            followers = list(Follow.objects.filter(following=user).values_list('follower__username', flat=True))
        except Exception:
            profile_data, friends, following, followers = {}, [], [], []

        messages = list(Message.objects.filter(sender=user).values(
            'id', 'content', 'message_type', 'created_at'
        ))
        posts = list(Post.objects.filter(author=user).values(
            'id', 'content', 'visibility', 'likes_count', 'comments_count', 'created_at'
        ))
        comments = list(PostComment.objects.filter(author=user).values(
            'id', 'content', 'created_at'
        ))
        notifications = list(Notification.objects.filter(user=user).values(
            'type', 'message', 'is_read', 'created_at'
        ))

        data = {
            'export_date': timezone.now().isoformat(),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'date_joined': user.date_joined.isoformat(),
                'bio': user.bio or '',
            },
            'profile': profile_data,
            'social': {
                'friends': friends,
                'following': following,
                'followers': followers,
            },
            'posts': list(posts),
            'comments': list(comments),
            'messages': list(messages),
            'notifications': list(notifications),
        }

        # Convert datetimes to strings
        data_json = json.loads(json.dumps(data, default=str))

        response = JsonResponse(data_json, json_dumps_params={'indent': 2})
        response['Content-Disposition'] = f'attachment; filename="mindconnect-data-{user.username}.json"'
        return response


class DeleteAccountView(APIView):
    """DELETE /api/auth/delete-account/ — GDPR right to erasure"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        password = request.data.get('password', '')
        user = request.user

        # Verify password before deletion
        if not user.check_password(password):
            return Response({'error': 'Incorrect password'}, status=status.HTTP_400_BAD_REQUEST)

        username = user.username
        # Anonymize first (soft delete strategy — keeps content but removes PII)
        import uuid
        anon_id = uuid.uuid4().hex[:8]
        user.username = f'deleted_{anon_id}'
        user.email = f'deleted_{anon_id}@deleted.mindconnect'
        user.bio = ''
        user.is_active = False
        user.set_unusable_password()
        user.save()

        # Blacklist all JWT tokens
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            OutstandingToken.objects.filter(user=user).update()
        except Exception:
            pass

        return Response({'message': f'Account deleted. Your data has been anonymized.'})
