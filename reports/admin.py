from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.html import format_html
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
import json

from .models import Report, AuditLog
from users.models import User
from chat.models import Room, Message
from notifications.models import Notification


class MindConnectAdminSite(AdminSite):
    site_header = '🧠 MindConnect Control Panel'
    site_title = 'MindConnect Admin'
    index_title = 'Platform Management'
    index_template = 'admin/custom_dashboard.html'

    def index(self, request, extra_context=None):
        """Inject analytics data into the admin dashboard."""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Core KPIs
        total_users = User.objects.count()
        active_users = User.objects.filter(is_online=True).count()
        new_users_today = User.objects.filter(date_joined__gte=today_start).count()
        new_users_week = User.objects.filter(date_joined__gte=week_ago).count()
        total_messages = Message.objects.count()
        messages_today = Message.objects.filter(created_at__gte=today_start).count()
        total_rooms = Room.objects.count()
        banned_users = User.objects.filter(is_active=False).count()
        pending_reports = Report.objects.filter(status='pending').count()
        auto_flagged = Report.objects.filter(auto_flagged=True, status='pending').count()

        # Try to get post counts
        try:
            from posts.models import Post
            total_posts = Post.objects.count()
            posts_today = Post.objects.filter(created_at__gte=today_start).count()
        except Exception:
            total_posts = 0
            posts_today = 0

        # Registration trend (last 14 days)
        reg_trend = []
        for i in range(13, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            count = User.objects.filter(date_joined__gte=day_start, date_joined__lt=day_end).count()
            reg_trend.append({'date': day.strftime('%b %d'), 'count': count})

        # Message volume trend (last 14 days)
        msg_trend = []
        for i in range(13, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            count = Message.objects.filter(created_at__gte=day_start, created_at__lt=day_end).count()
            msg_trend.append({'date': day.strftime('%b %d'), 'count': count})

        # Top active users
        top_users = User.objects.annotate(
            msg_count=Count('sent_messages', filter=Q(sent_messages__created_at__gte=week_ago))
        ).order_by('-msg_count')[:10]

        # Recent sign-ups
        recent_users = User.objects.order_by('-date_joined')[:10]

        # Most active rooms
        top_rooms = Room.objects.annotate(
            msg_count=Count('messages', filter=Q(messages__created_at__gte=week_ago))
        ).order_by('-msg_count')[:5]

        # Report summary
        report_by_type = Report.objects.values('reason').annotate(count=Count('id')).order_by('-count')[:8]

        extra_context = extra_context or {}
        extra_context.update({
            'kpis': {
                'total_users': total_users,
                'active_users': active_users,
                'new_users_today': new_users_today,
                'new_users_week': new_users_week,
                'total_messages': total_messages,
                'messages_today': messages_today,
                'total_rooms': total_rooms,
                'banned_users': banned_users,
                'pending_reports': pending_reports,
                'auto_flagged_reports': auto_flagged,
                'total_posts': total_posts,
                'posts_today': posts_today,
            },
            'reg_trend_json': json.dumps(reg_trend),
            'msg_trend_json': json.dumps(msg_trend),
            'top_users': top_users,
            'recent_users': recent_users,
            'top_rooms': top_rooms,
            'report_by_type': list(report_by_type),
        })
        return super().index(request, extra_context)


# Create custom admin site instance
custom_admin_site = MindConnectAdminSite(name='mindconnect_admin')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'target_type', 'reason', 'status_badge', 'auto_flagged', 'created_at')
    list_filter = ('status', 'target_type', 'reason', 'auto_flagged', 'created_at')
    search_fields = ('reporter__username', 'description')
    readonly_fields = ('reporter', 'target_type', 'target_id', 'created_at', 'auto_flagged')
    actions = ['approve_reports', 'dismiss_reports', 'mark_reviewing']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Report Info', {
            'fields': ('reporter', 'target_type', 'target_id', 'reason', 'description', 'auto_flagged')
        }),
        ('Resolution', {
            'fields': ('status', 'reviewed_by', 'reviewer_note')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'reviewing': '#3b82f6',
            'resolved_action': '#10b981',
            'resolved_dismissed': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:12px;font-size:11px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def approve_reports(self, request, queryset):
        queryset.update(status='resolved_action', reviewed_by=request.user)
        self._log_action(request, 'resolve_report', queryset.count())
        self.message_user(request, f"{queryset.count()} reports resolved — action taken.")

    def dismiss_reports(self, request, queryset):
        queryset.update(status='resolved_dismissed', reviewed_by=request.user)
        self.message_user(request, f"{queryset.count()} reports dismissed.")

    def mark_reviewing(self, request, queryset):
        queryset.update(status='reviewing')
        self.message_user(request, f"{queryset.count()} reports marked as under review.")

    def _log_action(self, request, action, count):
        AuditLog.objects.create(
            actor=request.user,
            action=action,
            details={'count': count},
            ip_address=request.META.get('REMOTE_ADDR')
        )

    approve_reports.short_description = "✅ Resolve — action taken"
    dismiss_reports.short_description = "❌ Dismiss selected reports"
    mark_reviewing.short_description = "🔍 Mark as under review"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('actor', 'action', 'target_user', 'ip_address', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('actor__username', 'target_user__username', 'ip_address')
    readonly_fields = ('actor', 'action', 'target_user', 'target_type', 'target_id', 'details', 'ip_address', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
