"""
Post share and repost views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Post, PostShare
from .serializers import PostSerializer
from notifications.models import Notification


class PostShareView(APIView):
    """POST /api/posts/<pk>/share/ — share/unshare a post"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        share, created = PostShare.objects.get_or_create(post=post, user=request.user)
        if not created:
            share.delete()
            Post.objects.filter(id=pk).update(shares_count=max(0, post.shares_count - 1))
            return Response({'shared': False, 'shares_count': max(0, post.shares_count - 1)})

        Post.objects.filter(id=pk).update(shares_count=post.shares_count + 1)
        if post.author != request.user:
            Notification.objects.create(
                user=post.author,
                type='post_like',  # Reuse existing type for now
                message=f'{request.user.username} shared your post',
                data={'post_id': post.id, 'user_id': request.user.id}
            )
        return Response({'shared': True, 'shares_count': post.shares_count + 1})


class RepostView(APIView):
    """POST /api/posts/<pk>/repost/ — create a new post that embeds the original"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        original = get_object_or_404(Post, id=pk)
        caption = request.data.get('caption', '').strip()

        repost = Post.objects.create(
            author=request.user,
            content=caption,
            visibility='public',
            shared_post=original,
            media=[],
            media_type='none',
        )
        return Response(PostSerializer(repost, context={'request': request}).data, status=201)
