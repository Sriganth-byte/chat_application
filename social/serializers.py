from rest_framework import serializers
from .models import FriendRequest, Friendship, Follow, UserProfile
from users.serializers import UserSerializer


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    friends_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    is_friend = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    pending_request = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'user', 'display_name', 'location', 'website', 'cover_photo',
            'is_private', 'show_online_status', 'allow_messages_from', 'theme',
            'followers_count', 'following_count', 'friends_count', 'posts_count',
            'is_friend', 'is_following', 'pending_request',
        ]
        read_only_fields = ['user']

    def get_followers_count(self, obj):
        return Follow.objects.filter(following=obj.user).count()

    def get_following_count(self, obj):
        return Follow.objects.filter(follower=obj.user).count()

    def get_friends_count(self, obj):
        from django.db.models import Q
        return Friendship.objects.filter(Q(user1=obj.user) | Q(user2=obj.user)).count()

    def get_posts_count(self, obj):
        return obj.user.posts.filter(visibility='public').count()

    def get_is_friend(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Friendship.are_friends(request.user, obj.user)

    def get_is_following(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Follow.objects.filter(follower=request.user, following=obj.user).exists()

    def get_pending_request(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        req = FriendRequest.objects.filter(
            sender=request.user, receiver=obj.user, status='pending'
        ).first()
        if req:
            return 'sent'
        req = FriendRequest.objects.filter(
            sender=obj.user, receiver=request.user, status='pending'
        ).first()
        if req:
            return 'received'
        return None


class FriendRequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)

    class Meta:
        model = FriendRequest
        fields = ['id', 'sender', 'receiver', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']


class FriendshipSerializer(serializers.ModelSerializer):
    user1 = UserSerializer(read_only=True)
    user2 = UserSerializer(read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'user1', 'user2', 'created_at']
