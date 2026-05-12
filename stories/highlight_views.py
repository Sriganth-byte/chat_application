"""
Story highlights API.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Story, StoryHighlight
from users.models import User


class StoryHighlightListView(APIView):
    """GET /api/stories/highlights/<username>/ — list highlights for a user"""
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        highlights = StoryHighlight.objects.filter(owner=user).prefetch_related('stories')
        data = [
            {
                'id': h.id,
                'title': h.title,
                'cover_url': h.cover_story.media_url if h.cover_story else (
                    h.stories.first().media_url if h.stories.exists() else ''
                ),
                'story_count': h.stories.count(),
                'created_at': h.created_at,
            }
            for h in highlights
        ]
        return Response(data)


class StoryHighlightDetailView(APIView):
    """GET/PATCH/DELETE /api/stories/highlights/detail/<id>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        h = get_object_or_404(StoryHighlight, id=pk)
        stories_data = [
            {
                'id': s.id,
                'media_url': s.media_url,
                'media_type': s.media_type,
                'text_content': s.text_content,
                'bg_color': s.bg_color,
                'text_color': s.text_color,
                'caption': s.caption,
                'created_at': s.created_at,
            }
            for s in h.stories.all()
        ]
        return Response({
            'id': h.id,
            'title': h.title,
            'owner': h.owner.username,
            'stories': stories_data,
            'created_at': h.created_at,
        })

    def patch(self, request, pk):
        h = get_object_or_404(StoryHighlight, id=pk, owner=request.user)
        h.title = request.data.get('title', h.title)
        story_ids = request.data.get('story_ids')
        if story_ids is not None:
            stories = Story.objects.filter(id__in=story_ids, author=request.user)
            h.stories.set(stories)
        cover_id = request.data.get('cover_story_id')
        if cover_id:
            h.cover_story_id = cover_id
        h.save()
        return Response({'updated': True, 'id': h.id})

    def delete(self, request, pk):
        h = get_object_or_404(StoryHighlight, id=pk, owner=request.user)
        h.delete()
        return Response(status=204)


class StoryHighlightCreateView(APIView):
    """POST /api/stories/highlights/create/ — create a new highlight"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        title = request.data.get('title', '').strip()
        story_ids = request.data.get('story_ids', [])
        if not title:
            return Response({'error': 'Title required'}, status=400)

        h = StoryHighlight.objects.create(
            owner=request.user,
            title=title[:30],
        )
        if story_ids:
            stories = Story.objects.filter(id__in=story_ids, author=request.user)
            h.stories.set(stories)
            if stories.exists():
                h.cover_story = stories.first()
                h.save()

        return Response({'id': h.id, 'title': h.title}, status=201)
