from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from datetime import timedelta
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Message, Room
from posts.models import Post
from reports.models import AuditLog, Report


User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'bio', 'is_active', 'is_staff',
            'is_superuser', 'is_verified', 'email_verified', 'date_joined',
            'last_seen', 'is_online', 'password',
        ]
        read_only_fields = ['id', 'date_joined', 'last_seen', 'is_online']

    def create(self, validated_data):
        password = self.initial_data.get('password') or get_random_string(16)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AdminPostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_username', 'content', 'visibility', 'status',
            'media_type', 'hashtags', 'likes_count', 'comments_count',
            'shares_count', 'views_count', 'is_pinned', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'author', 'author_username', 'likes_count', 'comments_count',
            'shares_count', 'views_count', 'created_at', 'updated_at',
        ]


class AdminReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'reporter', 'reporter_username', 'target_type', 'target_id',
            'reason', 'description', 'status', 'reviewer_note', 'reviewed_by',
            'reviewed_by_username', 'auto_flagged', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'reporter', 'reviewed_by', 'created_at', 'updated_at']


def _audit(actor, action, target_type='', target_id=None, target_user=None, details=None, request=None):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_user=target_user,
        details=details or {},
        ip_address=(request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                    or request.META.get('REMOTE_ADDR')) if request else None,
    )


class AdminDashboardView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        today = timezone.now() - timedelta(days=1)
        return Response({
            'users': {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
                'staff': User.objects.filter(is_staff=True).count(),
                'online': User.objects.filter(is_online=True).count(),
                'new_24h': User.objects.filter(date_joined__gte=today).count(),
            },
            'content': {
                'posts': Post.objects.count(),
                'published_posts': Post.objects.filter(status='published').count(),
                'messages': Message.objects.count(),
                'rooms': Room.objects.count(),
            },
            'moderation': {
                'pending_reports': Report.objects.filter(status='pending').count(),
                'auto_flagged': Report.objects.filter(auto_flagged=True).count(),
                'resolved': Report.objects.filter(status__startswith='resolved').count(),
            },
            'recent_reports': AdminReportSerializer(Report.objects.select_related('reporter')[:6], many=True).data,
            'recent_users': AdminUserSerializer(User.objects.order_by('-date_joined')[:6], many=True).data,
        })


class AdminUserListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        users = User.objects.all().order_by('-date_joined')
        if q:
            users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))
        return Response(AdminUserSerializer(users[:100], many=True).data)

    def post(self, request):
        serializer = AdminUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _audit(request.user, 'promote_admin' if user.is_staff else 'warn_user', 'user', user.id, user, {'created': True}, request)
        return Response(AdminUserSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminUserDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = AdminUserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _audit(request.user, 'promote_admin' if user.is_staff else 'unban_user', 'user', user.id, user, request.data, request)
        return Response(AdminUserSerializer(user).data)

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            return Response({'error': 'You cannot delete your own admin account'}, status=400)
        _audit(request.user, 'delete_account', 'user', user.id, user, {}, request)
        user.delete()
        return Response(status=204)


class AdminPostListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        posts = Post.objects.select_related('author').order_by('-created_at')
        if q:
            posts = posts.filter(content__icontains=q)
        return Response(AdminPostSerializer(posts[:100], many=True).data)

    def post(self, request):
        serializer = AdminPostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user)
        _audit(request.user, 'flag_content', 'post', post.id, details={'created': True}, request=request)
        return Response(AdminPostSerializer(post).data, status=201)


class AdminPostDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        serializer = AdminPostSerializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _audit(request.user, 'flag_content', 'post', post.id, details=request.data, request=request)
        return Response(AdminPostSerializer(post).data)

    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        _audit(request.user, 'delete_post', 'post', post.id, target_user=post.author, request=request)
        post.delete()
        return Response(status=204)


class AdminReportListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get('status')
        reports = Report.objects.select_related('reporter', 'reviewed_by')
        if status_filter:
            reports = reports.filter(status=status_filter)
        return Response(AdminReportSerializer(reports[:100], many=True).data)


class AdminReportDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        serializer = AdminReportSerializer(report, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(reviewed_by=request.user)
        _audit(request.user, 'resolve_report', 'report', report.id, details=request.data, request=request)
        return Response(AdminReportSerializer(report).data)


class AdminAuditLogView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        logs = AuditLog.objects.select_related('actor', 'target_user')[:100]
        return Response([
            {
                'id': log.id,
                'actor': log.actor.username if log.actor else 'system',
                'action': log.action,
                'target_type': log.target_type,
                'target_id': log.target_id,
                'target_user': log.target_user.username if log.target_user else None,
                'details': log.details,
                'created_at': log.created_at,
            }
            for log in logs
        ])
