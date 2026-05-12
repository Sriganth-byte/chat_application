"""
Post analytics API views.
GET  /api/posts/<id>/analytics/     — creator analytics for own post
GET  /api/auth/analytics/           — profile-level analytics (follower growth, reach)
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Sum, Count, Q

from posts.models import Post, PostLike, PostComment, PostSave, PostAnalytics
from social.models import Follow, Friendship


class PostAnalyticsView(APIView):
    """GET /api/posts/<pk>/analytics/ — post-level analytics (owner only)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        post = get_object_or_404(Post, id=pk, author=request.user)
        today = timezone.now().date()
        days_30 = today - timedelta(days=29)

        # Daily analytics from PostAnalytics table (last 30 days)
        daily = list(
            PostAnalytics.objects.filter(post=post, date__gte=days_30)
            .order_by('date')
            .values('date', 'views', 'likes', 'comments', 'shares', 'saves', 'reach')
        )

        # Fill missing days with zeros
        daily_map = {str(d['date']): d for d in daily}
        chart = []
        for i in range(30):
            d = days_30 + timedelta(days=i)
            key = str(d)
            chart.append({
                'date': key,
                **daily_map.get(key, {'views': 0, 'likes': 0, 'comments': 0, 'shares': 0, 'saves': 0, 'reach': 0})
            })

        return Response({
            'post_id': post.id,
            'summary': {
                'views': post.views_count,
                'likes': post.likes_count,
                'comments': post.comments_count,
                'shares': post.shares_count,
                'saves': post.saves.count(),
                'impressions': post.impressions_count,
                'engagement_rate': round(
                    (post.likes_count + post.comments_count + post.shares_count) / max(post.views_count, 1) * 100, 2
                ),
            },
            'chart': chart,
        })


class ProfileAnalyticsView(APIView):
    """GET /api/auth/analytics/ — profile-level analytics"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        days_30 = today - timedelta(days=29)
        days_7 = today - timedelta(days=6)

        # Follower growth over 30 days (approximation via join date bucketing)
        posts = Post.objects.filter(author=user, status='published')

        # Aggregate stats
        total_likes = PostLike.objects.filter(post__author=user).count()
        total_comments = PostComment.objects.filter(post__author=user).count()
        total_saves = PostSave.objects.filter(post__author=user).count()
        followers_count = Follow.objects.filter(following=user).count()
        following_count = Follow.objects.filter(follower=user).count()

        # Top performing posts
        top_posts = posts.order_by('-likes_count')[:5].values(
            'id', 'content', 'likes_count', 'comments_count', 'views_count', 'created_at'
        )

        # Posts last 7 days vs previous 7 days
        posts_last_7 = posts.filter(created_at__date__gte=days_7).count()
        posts_prev_7 = posts.filter(
            created_at__date__gte=days_7 - timedelta(days=7),
            created_at__date__lt=days_7
        ).count()

        # Likes last 7 days
        likes_last_7 = PostLike.objects.filter(
            post__author=user,
            created_at__date__gte=days_7
        ).count()

        return Response({
            'summary': {
                'total_posts': posts.count(),
                'total_likes': total_likes,
                'total_comments': total_comments,
                'total_saves': total_saves,
                'followers': followers_count,
                'following': following_count,
            },
            'trends': {
                'posts_last_7_days': posts_last_7,
                'posts_change': posts_last_7 - posts_prev_7,
                'likes_last_7_days': likes_last_7,
            },
            'top_posts': list(top_posts),
        })
