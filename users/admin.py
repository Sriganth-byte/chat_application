from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Enhanced Admin for User model — production-grade management"""
    list_display = (
        'avatar_display',
        'username',
        'email',
        'status_badge',
        'online_indicator',
        'messages_sent_week',
        'last_seen_display',
        'date_joined',
        'email_verified_badge',
        'is_active',
    )
    list_filter = (
        'is_online', 'is_active', 'email_verified',
        'date_joined', 'last_seen',
        ('date_joined', admin.DateFieldListFilter),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = (
        'last_seen', 'date_joined', 'last_login',
        'active_sessions', 'activity_summary'
    )
    ordering = ('-date_joined',)
    list_per_page = 30
    show_full_result_count = False  # Performance for large datasets

    fieldsets = (
        ('👤 Identity', {
            'fields': ('username', 'email', 'password', 'bio', 'avatar')
        }),
        ('🟢 Presence', {
            'fields': ('is_online', 'last_seen', 'active_sessions'),
            'classes': ('collapse',)
        }),
        ('📊 Activity', {
            'fields': ('activity_summary',),
            'classes': ('collapse',)
        }),
        ('🔐 Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'email_verified', 'groups', 'user_permissions'),
        }),
        ('📅 Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'ban_users', 'unban_users', 'mark_offline',
        'verify_emails', 'export_users_csv', 'send_system_notification'
    ]

    def get_queryset(self, request):
        week_ago = timezone.now() - timedelta(days=7)
        return super().get_queryset(request).annotate(
            msg_count_week=Count(
                'sent_messages',
                filter=Q(sent_messages__created_at__gte=week_ago)
            )
        )

    def avatar_display(self, obj):
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return format_html(
                '<img src="{}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">',
                obj.avatar.url
            )
        initials = (obj.username[0] if obj.username else '?').upper()
        return format_html(
            '<div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#6c63ff,#a855f7);'
            'display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:12px;">{}</div>',
            initials
        )
    avatar_display.short_description = ''

    def status_badge(self, obj):
        if not obj.is_active:
            return format_html(
                '<span style="background:#ef4444;color:white;padding:2px 8px;border-radius:12px;font-size:11px;">BANNED</span>'
            )
        if obj.is_superuser:
            return format_html(
                '<span style="background:linear-gradient(135deg,#6c63ff,#a855f7);color:white;padding:2px 8px;border-radius:12px;font-size:11px;">SUPERUSER</span>'
            )
        if obj.is_staff:
            return format_html(
                '<span style="background:#3b82f6;color:white;padding:2px 8px;border-radius:12px;font-size:11px;">STAFF</span>'
            )
        return format_html(
            '<span style="background:#374151;color:#9ca3af;padding:2px 8px;border-radius:12px;font-size:11px;">USER</span>'
        )
    status_badge.short_description = 'Role'

    def online_indicator(self, obj):
        if obj.is_online:
            return format_html('<span style="color:#10b981;font-size:16px;" title="Online">●</span>')
        return format_html('<span style="color:#4b5563;font-size:16px;" title="Offline">●</span>')
    online_indicator.short_description = '🟢'

    def email_verified_badge(self, obj):
        if obj.email_verified:
            return format_html('<span style="color:#10b981;">✓ Verified</span>')
        return format_html('<span style="color:#f59e0b;">⚠ Unverified</span>')
    email_verified_badge.short_description = 'Email'

    def last_seen_display(self, obj):
        if not obj.last_seen:
            return '—'
        delta = timezone.now() - obj.last_seen
        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                mins = delta.seconds // 60
                return f'{mins}m ago'
            return f'{hours}h ago'
        return f'{delta.days}d ago'
    last_seen_display.short_description = 'Last Seen'

    def messages_sent_week(self, obj):
        count = getattr(obj, 'msg_count_week', 0)
        if count > 100:
            color = '#10b981'
        elif count > 20:
            color = '#3b82f6'
        else:
            color = '#64748b'
        return format_html('<span style="color:{};">{}</span>', color, count)
    messages_sent_week.short_description = 'Msgs (7d)'
    messages_sent_week.admin_order_field = 'msg_count_week'

    def activity_summary(self, obj):
        week_ago = timezone.now() - timedelta(days=7)
        msg_count = obj.sent_messages.count()
        msg_week = obj.sent_messages.filter(created_at__gte=week_ago).count()
        room_count = obj.rooms.count()
        return format_html(
            '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;padding:8px 0;">'
            '<div><strong style="font-size:1.4rem;">{}</strong><br><span style="color:#6b7280;font-size:12px;">Total Messages</span></div>'
            '<div><strong style="font-size:1.4rem;">{}</strong><br><span style="color:#6b7280;font-size:12px;">Messages This Week</span></div>'
            '<div><strong style="font-size:1.4rem;">{}</strong><br><span style="color:#6b7280;font-size:12px;">Rooms Joined</span></div>'
            '</div>',
            msg_count, msg_week, room_count
        )
    activity_summary.short_description = 'Activity Summary'

    # ─── Admin Actions ───────────────────────────────────────────

    def ban_users(self, request, queryset):
        count = queryset.exclude(is_superuser=True).update(is_active=False)
        self._audit(request, 'ban_user', count)
        self.message_user(request, f"⛔ {count} users banned.")
    ban_users.short_description = "⛔ Ban selected users"

    def unban_users(self, request, queryset):
        count = queryset.update(is_active=True)
        self._audit(request, 'unban_user', count)
        self.message_user(request, f"✅ {count} users unbanned.")
    unban_users.short_description = "✅ Unban selected users"

    def mark_offline(self, request, queryset):
        queryset.update(is_online=False, active_sessions=[])
        self.message_user(request, "Users marked as offline.")
    mark_offline.short_description = "🔌 Mark offline"

    def verify_emails(self, request, queryset):
        count = queryset.update(email_verified=True, verification_token=None)
        self.message_user(request, f"✉️ {count} emails verified.")
    verify_emails.short_description = "✉️ Force-verify email"

    def export_users_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mindconnect_users.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Username', 'Email', 'Date Joined', 'Is Active', 'Email Verified', 'Is Online'])
        for user in queryset:
            writer.writerow([
                user.id, user.username, user.email,
                user.date_joined.strftime('%Y-%m-%d'),
                user.is_active, user.email_verified, user.is_online
            ])
        return response
    export_users_csv.short_description = "📥 Export to CSV"

    def send_system_notification(self, request, queryset):
        from notifications.models import Notification
        message = "Important: MindConnect system maintenance scheduled. Thank you for your patience."
        for user in queryset:
            Notification.objects.create(
                user=user,
                type='system',
                message=message,
                data={'from': 'admin'}
            )
        self.message_user(request, f"📢 Notification sent to {queryset.count()} users.")
    send_system_notification.short_description = "📢 Send system notification"

    def _audit(self, request, action, count):
        try:
            from reports.models import AuditLog
            AuditLog.objects.create(
                actor=request.user,
                action=action,
                details={'count': count},
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass
