from django.contrib import admin
from .models import Post, PostLike, PostComment, PostShare, PostSave
from django.utils.html import format_html
from django.db.models import Count


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'content_preview', 'visibility', 'likes_count', 'comments_count', 'views_count', 'created_at')
    list_filter = ('visibility', 'media_type', 'created_at')
    search_fields = ('author__username', 'content')
    readonly_fields = ('created_at', 'updated_at', 'likes_count', 'comments_count', 'shares_count', 'views_count')
    date_hierarchy = 'created_at'
    actions = ['delete_selected']

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Content'


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'content_preview', 'created_at')
    search_fields = ('author__username', 'content')
    readonly_fields = ('created_at',)

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = 'Content'
