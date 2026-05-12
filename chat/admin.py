from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from .models import Room, Message, RoomMember


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """Admin configuration for Room model"""
    list_display = (
        'name',
        'type',
        'created_by',
        'created_at_display',
        'member_count',
        'message_count'
    )
    list_filter = ('type', 'created_at')
    search_fields = ('name', 'description', 'created_by__username')
    readonly_fields = ('created_at',)
    filter_horizontal = ('admins',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'type', 'created_by', 'avatar', 'description')
        }),
        ('Administrators', {
            'fields': ('admins',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            member_count=models.Count('members', distinct=True),
            message_count=models.Count('messages', distinct=True)
        )

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'
    member_count.admin_order_field = 'member_count'

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'
    message_count.admin_order_field = 'message_count'

    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = 'Created'
    created_at_display.admin_order_field = 'created_at'


@admin.register(RoomMember)
class RoomMemberAdmin(admin.ModelAdmin):
    """Admin configuration for RoomMember model"""
    list_display = ('user', 'room', 'role', 'joined_at_display')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__username', 'room__name')
    readonly_fields = ('joined_at',)

    def joined_at_display(self, obj):
        return obj.joined_at.strftime('%Y-%m-%d %H:%M')
    joined_at_display.short_description = 'Joined'
    joined_at_display.admin_order_field = 'joined_at'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin configuration for Message model"""
    list_display = (
        'sender',
        'room',
        'message_type',
        'content_short',
        'created_at_display',
        'is_seen',
        'edited'
    )
    list_filter = ('message_type', 'is_seen', 'edited', 'created_at')
    search_fields = ('content', 'sender__username', 'room__name')
    readonly_fields = ('sender', 'room', 'created_at', 'edited_at')
    date_hierarchy = 'created_at'

    def content_short(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_short.short_description = 'Content'

    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = 'Sent'
    created_at_display.admin_order_field = 'created_at'
