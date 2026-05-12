from django.contrib import admin
from .models import Story, StoryView


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('author', 'media_type', 'views_count', 'expires_at', 'created_at')
    list_filter = ('media_type', 'created_at')
    search_fields = ('author__username', 'caption')
    readonly_fields = ('created_at', 'views_count')
    actions = ['delete_selected']
