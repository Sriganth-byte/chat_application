from rest_framework import serializers
from users.serializers import UserSerializer
from .models import Room, Message, RoomMember
from backend.utils.media_url import to_relative_url


class RoomMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = RoomMember
        fields = ['user', 'role', 'joined_at']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model"""
    sender = UserSerializer(read_only=True)
    reply_to_data = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'room', 'sender', 'message_type', 'content',
            'file_url', 'file_name', 'file_size', 'one_time',
            'one_time_consumed', 'is_seen', 'edited', 'created_at',
            'reply_to_data'
        ]

    def get_content(self, obj):
        """Normalise localhost media URLs stored in content to root-relative paths."""
        if obj.message_type and obj.message_type != 'text':
            return to_relative_url(obj.content)
        return obj.content

    one_time_consumed = serializers.SerializerMethodField()

    def get_one_time_consumed(self, obj):
        user_id = None
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
        else:
            user_id = self.context.get('user_id')
        if not user_id:
            return False
        return obj.one_time_read_by.filter(id=user_id).exists()

    def get_reply_to_data(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'content': obj.reply_to.content[:100],
                'sender': obj.reply_to.sender.username
            }
        return None


class RoomSerializer(serializers.ModelSerializer):
    """Serializer for Room model with nested data"""
    members = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id', 'name', 'type', 'avatar', 'description',
            'created_at', 'members', 'last_message', 'unread_count'
        ]

    def get_members(self, obj):
        members = obj.members.select_related('user')[:10]
        return RoomMemberSerializer(members, many=True).data

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last:
            return {
                'content': last.content[:100],
                'sender': last.sender.username,
                'created_at': last.created_at.isoformat(),
                'message_type': last.message_type
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                membership = obj.members.get(user=request.user)
                if membership.last_read:
                    return obj.messages.filter(created_at__gt=membership.last_read).count()
                return obj.messages.count()
            except RoomMember.DoesNotExist:
                return 0
        return 0


class RoomCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating rooms"""
    members = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Room
        fields = ['name', 'type', 'avatar', 'description', 'members']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True, 'default': ''},
        }

    def create(self, validated_data):
        # 'members' is a list of user IDs handled by the view manually —
        # pop it here so DRF doesn't try to set the M2M with raw integers
        validated_data.pop('members', None)
        return super().create(validated_data)



class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    room_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Message
        fields = ['room_id', 'message_type', 'content', 'one_time']
