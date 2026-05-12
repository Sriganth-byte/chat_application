from rest_framework import serializers
from .models import Story, StoryView, StoryReaction
from users.serializers import UserSerializer


class StorySerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    is_viewed = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            'id', 'author', 'media_url', 'media_type', 'text_content',
            'text_color', 'bg_color', 'caption', 'expires_at', 'created_at',
            'views_count', 'is_viewed', 'is_active'
        ]
        read_only_fields = ['id', 'author', 'expires_at', 'created_at', 'views_count']

    def get_is_viewed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.story_views.filter(viewer=request.user).exists()

    def get_is_active(self, obj):
        return obj.is_active()


class StoryGroupSerializer(serializers.Serializer):
    """Groups stories by user for the story bar."""
    user = UserSerializer(read_only=True)
    stories = StorySerializer(many=True, read_only=True)
    has_unseen = serializers.BooleanField(read_only=True)
    latest_story_time = serializers.DateTimeField(read_only=True)
