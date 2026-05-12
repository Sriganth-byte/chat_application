from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Story, StoryView, StoryReaction
from .serializers import StorySerializer
from social.models import Friendship, Follow
from users.models import User
from users.serializers import UserSerializer


class StoryListView(APIView):
    """GET /api/stories/ — stories from friends and following, grouped by user"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        friend_ids = set(Friendship.get_friends(user).values_list('id', flat=True))
        following_ids = set(Follow.objects.filter(follower=user).values_list('following_id', flat=True))
        visible_ids = friend_ids | following_ids | {user.id}

        now = timezone.now()
        active_stories = Story.objects.filter(
            author_id__in=visible_ids,
            expires_at__gt=now
        ).select_related('author').order_by('author_id', '-created_at')

        # Group by author
        story_map = {}
        for story in active_stories:
            aid = story.author_id
            if aid not in story_map:
                story_map[aid] = {'user': story.author, 'stories': [], 'has_unseen': False}
            story_map[aid]['stories'].append(story)
            if not story.story_views.filter(viewer=user).exists():
                story_map[aid]['has_unseen'] = True

        # My stories first, then unseen, then seen
        result = list(story_map.values())
        result.sort(key=lambda x: (
            0 if x['user'].id == user.id else 1,
            0 if x['has_unseen'] else 1
        ))

        response = []
        for group in result:
            response.append({
                'user': UserSerializer(group['user'], context={'request': request}).data,
                'stories': StorySerializer(group['stories'], many=True, context={'request': request}).data,
                'has_unseen': group['has_unseen'],
                'latest_story_time': group['stories'][0].created_at.isoformat() if group['stories'] else None,
            })
        return Response(response)


class StoryCreateView(APIView):
    """POST /api/stories/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        media_url = request.data.get('media_url', '')
        media_type = request.data.get('media_type', 'image')
        text_content = request.data.get('text_content', '')
        caption = request.data.get('caption', '')

        if not media_url and not text_content:
            return Response({'error': 'Media URL or text content required'}, status=400)

        story = Story.objects.create(
            author=request.user,
            media_url=media_url,
            media_type=media_type,
            text_content=text_content,
            text_color=request.data.get('text_color', '#ffffff'),
            bg_color=request.data.get('bg_color', '#6c63ff'),
            caption=caption,
        )
        return Response(StorySerializer(story, context={'request': request}).data, status=201)


class StoryViewView(APIView):
    """POST /api/stories/<id>/view/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        story = get_object_or_404(Story, id=pk)
        if story.author == request.user:
            return Response({'message': 'Own story'})
        _, created = StoryView.objects.get_or_create(story=story, viewer=request.user)
        if created:
            Story.objects.filter(id=pk).update(views_count=story.views_count + 1)
        return Response({'viewed': True})


class StoryDeleteView(APIView):
    """DELETE /api/stories/<id>/"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        story = get_object_or_404(Story, id=pk, author=request.user)
        story.delete()
        return Response(status=204)
