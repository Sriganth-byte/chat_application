from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    class Meta:
        model = Notification
        fields = ['id', 'type', 'message', 'data', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']
