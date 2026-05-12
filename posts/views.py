from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db import models as django_models
from django.db.models import Q, Count as models_Count
from django.core.cache import cache

from .models import Post, PostLike, PostComment, PostShare, PostSave, CommentLike, Poll, PollOption, PollVote
from .serializers import PostSerializer, PostCommentSerializer
from social.models import Friendship, Follow
from notifications.models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import re


def _extract_hashtags(content):
    return re.findall(r'#(\w+)', content)


class FeedPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50


class FeedView(generics.ListAPIView):
    """GET /api/posts/feed/ — personalized feed + public discovery"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer
    pagination_class = FeedPagination

    def get_queryset(self):
        user = self.request.user
        blocked_ids = set(user.blocked_users.values_list('id', flat=True))

        friend_ids = set(Friendship.get_friends(user).values_list('id', flat=True))
        following_ids = set(Follow.objects.filter(follower=user).values_list('following_id', flat=True))
        social_ids = friend_ids | following_ids | {user.id}

        base_qs = Post.objects.filter(
            status='published'
        ).exclude(
            author_id__in=blocked_ids
        ).select_related('author', 'shared_post__author').prefetch_related(
            'likes', 'saves', 'poll__options'
        )

        # Section 1: personal feed posts (friends + follows)
        personal = base_qs.filter(author_id__in=social_ids)

        # Section 2: public posts NOT already in personal
        public_discovery = base_qs.filter(
            visibility='public'
        ).exclude(author_id__in=social_ids)

        # Merge: personal first (by recency), then public discovery
        from itertools import chain
        personal_ids = list(personal.values_list('id', flat=True))
        public_ids   = list(public_discovery.values_list('id', flat=True))

        # Return combined ordered queryset using CASE ordering
        from django.db.models import Case, When, IntegerField
        all_ids = personal_ids + public_ids
        if not all_ids:
            return base_qs.none()

        preserved = Case(
            *[When(id=pk, then=pos) for pos, pk in enumerate(all_ids)],
            output_field=IntegerField()
        )
        return base_qs.filter(id__in=all_ids).order_by(preserved)


class PostCreateView(APIView):
    """POST /api/posts/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        content = request.data.get('content', '').strip()
        poll_data = request.data.get('poll')
        if not content and not request.data.get('media') and not poll_data:
            return Response({'error': 'Content, media, or poll required'}, status=400)

        hashtags = _extract_hashtags(content)
        post = Post.objects.create(
            author=request.user,
            content=content,
            visibility=request.data.get('visibility', 'public'),
            media=request.data.get('media', []),
            media_type=request.data.get('media_type', 'none'),
            hashtags=hashtags,
        )

        # Create poll if provided
        if poll_data:
            question = poll_data.get('question', '').strip()
            options = [o.strip() for o in poll_data.get('options', []) if o.strip()]
            if question and len(options) >= 2:
                p = Poll.objects.create(post=post, question=question)
                for i, opt_text in enumerate(options):
                    PollOption.objects.create(poll=p, text=opt_text, order=i)

        # Trigger background tasks
        try:
            from users.tasks import process_mentions, fetch_link_preview, invalidate_feed_cache
            process_mentions.delay(post.id)
            if 'http' in content:
                fetch_link_preview.delay(post.id)
            invalidate_feed_cache.delay(request.user.id)
        except Exception:
            pass

        return Response(PostSerializer(post, context={'request': request}).data, status=201)


class PostDetailView(APIView):
    """GET/PATCH/DELETE /api/posts/<id>/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        # Increment view count
        Post.objects.filter(id=pk).update(views_count=post.views_count + 1)
        return Response(PostSerializer(post, context={'request': request}).data)

    def patch(self, request, pk):
        post = get_object_or_404(Post, id=pk, author=request.user)
        content = request.data.get('content', post.content).strip()
        post.content = content
        post.hashtags = _extract_hashtags(content)
        post.visibility = request.data.get('visibility', post.visibility)
        post.edited = True
        post.edited_at = timezone.now()
        post.save()
        return Response(PostSerializer(post, context={'request': request}).data)

    def delete(self, request, pk):
        post = get_object_or_404(Post, id=pk, author=request.user)
        post.delete()
        return Response(status=204)


class PostLikeView(APIView):
    """POST /api/posts/<id>/like/ — toggle like"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        like, created = PostLike.objects.get_or_create(post=post, user=request.user)
        if created:
            Post.objects.filter(id=pk).update(likes_count=post.likes_count + 1)
            if post.author != request.user:
                Notification.objects.create(
                    user=post.author,
                    type='post_like',
                    message=f'{request.user.username} liked your post',
                    data={'post_id': post.id, 'user_id': request.user.id}
                )
            return Response({'liked': True, 'likes_count': post.likes_count + 1})
        else:
            like.delete()
            Post.objects.filter(id=pk).update(likes_count=max(0, post.likes_count - 1))
            return Response({'liked': False, 'likes_count': max(0, post.likes_count - 1)})


class PostSaveView(APIView):
    """POST /api/posts/<id>/save/ — toggle save/bookmark"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        save, created = PostSave.objects.get_or_create(post=post, user=request.user)
        if not created:
            save.delete()
            return Response({'saved': False})
        return Response({'saved': True})


class PostCommentListView(APIView):
    """GET/POST /api/posts/<id>/comments/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        comments = post.comments.filter(parent=None).select_related('author').order_by('-created_at')
        return Response(PostCommentSerializer(comments, many=True, context={'request': request}).data)

    def post(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Comment content required'}, status=400)

        parent_id = request.data.get('parent_id')
        parent = None
        if parent_id:
            parent = get_object_or_404(PostComment, id=parent_id, post=post)

        comment = PostComment.objects.create(
            post=post, author=request.user, content=content, parent=parent
        )
        Post.objects.filter(id=pk).update(comments_count=post.comments_count + 1)

        if post.author != request.user:
            Notification.objects.create(
                user=post.author,
                type='post_comment',
                message=f'{request.user.username} commented on your post',
                data={'post_id': post.id, 'comment_id': comment.id}
            )
        return Response(PostCommentSerializer(comment, context={'request': request}).data, status=201)


COMMENT_EDIT_WINDOW = 15 * 60  # 15 minutes in seconds

class CommentDetailView(APIView):
    """PATCH/DELETE /api/posts/comments/<id>/ — edit or delete a comment"""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        comment = get_object_or_404(PostComment, id=pk)
        if comment.author != request.user:
            return Response({'error': 'Not your comment'}, status=403)
        age = (timezone.now() - comment.created_at).total_seconds()
        if age > COMMENT_EDIT_WINDOW:
            return Response({'error': 'Edit window expired (15 min)'}, status=400)
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Content required'}, status=400)
        comment.content = content
        comment.edited = True
        comment.save(update_fields=['content', 'edited'])
        return Response(PostCommentSerializer(comment, context={'request': request}).data)

    def delete(self, request, pk):
        comment = get_object_or_404(PostComment, id=pk)
        # Allow owner OR post author to delete
        if comment.author != request.user and comment.post.author != request.user:
            return Response({'error': 'Permission denied'}, status=403)
        post = comment.post
        comment.delete()
        Post.objects.filter(id=post.id).update(
            comments_count=max(0, post.comments_count - 1)
        )
        return Response(status=204)


class CommentLikeView(APIView):
    """POST /api/posts/comments/<id>/like/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        comment = get_object_or_404(PostComment, id=pk)
        like, created = CommentLike.objects.get_or_create(comment=comment, user=request.user)
        if created:
            PostComment.objects.filter(id=pk).update(likes_count=comment.likes_count + 1)
            return Response({'liked': True})
        like.delete()
        PostComment.objects.filter(id=pk).update(likes_count=max(0, comment.likes_count - 1))
        return Response({'liked': False})


class SavedPostsView(generics.ListAPIView):
    """GET /api/posts/saved/ — bookmarked posts"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer
    pagination_class = FeedPagination

    def get_queryset(self):
        saved_ids = PostSave.objects.filter(user=self.request.user).values_list('post_id', flat=True)
        return Post.objects.filter(id__in=saved_ids).select_related('author')


class UserPostsView(generics.ListAPIView):
    """GET /api/posts/user/<username>/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer
    pagination_class = FeedPagination

    def get_queryset(self):
        from users.models import User
        user = get_object_or_404(User, username=self.kwargs['username'])
        return Post.objects.filter(author=user, visibility='public').select_related('author')


class TrendingHashtagsView(APIView):
    """GET /api/posts/trending/ — trending hashtags (cached 5 min)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cached = cache.get('trending_hashtags')
        if cached:
            return Response(cached)

        # Aggregate hashtags from all published posts
        # Filter out null/empty arrays — works across PostgreSQL and SQLite
        tag_counts = {}
        posts_with_tags = Post.objects.filter(
            status='published',
            visibility='public',
        ).exclude(hashtags__isnull=True).exclude(hashtags=[])

        for post in posts_with_tags.only('hashtags'):
            for tag in (post.hashtags or []):
                if tag:  # skip empty strings
                    tag_counts[tag.lower()] = tag_counts.get(tag.lower(), 0) + 1

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        result = [{'tag': t, 'count': c} for t, c in sorted_tags]
        cache.set('trending_hashtags', result, timeout=300)
        return Response(result)


class PollVoteView(APIView):
    """POST /api/posts/<pk>/poll/vote/ — cast or change a poll vote"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        poll = get_object_or_404(Poll, post=post)
        option_id = request.data.get('option_id')
        option = get_object_or_404(PollOption, id=option_id, poll=poll)

        # Remove existing vote on any option in this poll
        PollVote.objects.filter(option__poll=poll, voter=request.user).delete()
        # Cast new vote
        PollVote.objects.create(option=option, voter=request.user)

        # Return updated option counts
        options_data = [
            {
                'id': opt.id,
                'text': opt.text,
                'vote_count': opt.votes.count(),
                'order': opt.order,
            }
            for opt in poll.options.all()
        ]
        return Response({'options': options_data})


class HashtagFeedView(generics.ListAPIView):
    """GET /api/posts/hashtag/<tag>/ — posts with a specific hashtag"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer
    pagination_class = FeedPagination

    def get_queryset(self):
        tag = self.kwargs['tag'].lower().lstrip('#')
        return Post.objects.filter(
            hashtags__contains=[tag],
            visibility='public',
            status='published',
        ).select_related('author').order_by('-likes_count', '-created_at')


class SavedCollectionsView(APIView):
    """GET/POST /api/posts/saved/collections/ — manage saved post collections"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import SavedCollection
        collections = SavedCollection.objects.filter(owner=request.user).annotate(
            item_count=models_Count('items')
        )
        return Response([
            {
                'id': c.id,
                'name': c.name,
                'emoji': c.emoji,
                'is_private': c.is_private,
                'item_count': c.item_count,
                'created_at': c.created_at,
            }
            for c in collections
        ])

    def post(self, request):
        from .models import SavedCollection
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'error': 'Name required'}, status=400)
        col, created = SavedCollection.objects.get_or_create(
            owner=request.user, name=name[:100],
            defaults={
                'emoji': request.data.get('emoji', '🔖'),
                'is_private': request.data.get('is_private', True),
            }
        )
        return Response({'id': col.id, 'name': col.name, 'created': created}, status=201 if created else 200)


class ScheduledPostsView(generics.ListAPIView):
    """GET /api/posts/scheduled/ — list own scheduled posts"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer

    def get_queryset(self):
        return Post.objects.filter(
            author=self.request.user,
            status='scheduled'
        ).select_related('author').order_by('publish_at')
