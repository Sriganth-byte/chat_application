from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta


class ProfileAnalyticsView(APIView):
    """GET /api/auth/analytics/ — user profile analytics"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from posts.models import Post, PostLike, PostComment, PostSave
        from social.models import Follow

        user = request.user
        today = timezone.now().date()
        days_7 = today - timedelta(days=6)
        days_7_prev = days_7 - timedelta(days=7)

        posts = Post.objects.filter(author=user, status='published')
        total_likes = PostLike.objects.filter(post__author=user).count()
        total_comments = PostComment.objects.filter(post__author=user).count()
        total_saves = PostSave.objects.filter(post__author=user).count()
        followers = Follow.objects.filter(following=user).count()
        following = Follow.objects.filter(follower=user).count()

        posts_last_7 = posts.filter(created_at__date__gte=days_7).count()
        posts_prev_7 = posts.filter(
            created_at__date__gte=days_7_prev, created_at__date__lt=days_7
        ).count()
        likes_last_7 = PostLike.objects.filter(post__author=user, created_at__date__gte=days_7).count()

        top_posts = list(posts.order_by('-likes_count')[:5].values(
            'id', 'content', 'likes_count', 'comments_count', 'views_count', 'created_at'
        ))

        return Response({
            'summary': {
                'total_posts': posts.count(),
                'total_likes': total_likes,
                'total_comments': total_comments,
                'total_saves': total_saves,
                'followers': followers,
                'following': following,
            },
            'trends': {
                'posts_last_7_days': posts_last_7,
                'posts_change': posts_last_7 - posts_prev_7,
                'likes_last_7_days': likes_last_7,
            },
            'top_posts': top_posts,
        })
