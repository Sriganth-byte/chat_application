from rest_framework import serializers
from .models import Post, PostLike, PostComment, PostShare, PostSave, Poll, PollOption, PollVote
from users.serializers import UserSerializer
from backend.utils.media_url import normalise_media_list


class PostCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = PostComment
        fields = [
            'id', 'author', 'content', 'parent', 'likes_count', 'edited',
            'created_at', 'updated_at', 'is_liked', 'replies'
        ]
        read_only_fields = ['id', 'author', 'likes_count', 'edited', 'created_at', 'updated_at']

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.comment_likes.filter(user=request.user).exists()

    def get_replies(self, obj):
        if obj.parent is not None:
            return []
        replies = obj.replies.select_related('author').order_by('created_at')[:10]
        return PostCommentSerializer(replies, many=True, context=self.context).data


class PollOptionSerializer(serializers.ModelSerializer):
    vote_count = serializers.SerializerMethodField()

    class Meta:
        model = PollOption
        fields = ['id', 'text', 'order', 'vote_count']

    def get_vote_count(self, obj):
        return obj.votes.count()


class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)
    user_vote = serializers.SerializerMethodField()
    total_votes = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ['id', 'question', 'closes_at', 'options', 'user_vote', 'total_votes']

    def get_user_vote(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        vote = PollVote.objects.filter(
            option__poll=obj, voter=request.user
        ).select_related('option').first()
        return vote.option_id if vote else None

    def get_total_votes(self, obj):
        return PollVote.objects.filter(option__poll=obj).count()


class SharedPostSerializer(serializers.ModelSerializer):
    """Lightweight serializer for embedded reposts."""
    author = UserSerializer(read_only=True)
    media = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'author', 'content', 'media', 'media_type', 'created_at']

    def get_media(self, obj):
        return normalise_media_list(obj.media)


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    top_comments = serializers.SerializerMethodField()
    poll = serializers.SerializerMethodField()
    shared_post = SharedPostSerializer(read_only=True)
    link_preview = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'content', 'visibility', 'media', 'media_type',
            'hashtags', 'is_pinned', 'edited', 'edited_at',
            'likes_count', 'comments_count', 'shares_count', 'views_count',
            'created_at', 'updated_at', 'is_liked', 'is_saved',
            'top_comments', 'poll', 'shared_post', 'link_preview',
        ]
        read_only_fields = [
            'id', 'author', 'likes_count', 'comments_count', 'shares_count',
            'views_count', 'edited_at', 'created_at', 'updated_at'
        ]

    def get_media(self, obj):
        """Normalise stored localhost URLs to root-relative paths."""
        return normalise_media_list(obj.media)

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.saves.filter(user=request.user).exists()

    def get_top_comments(self, obj):
        top = obj.comments.filter(parent=None).select_related('author').order_by('-created_at')[:3]
        return PostCommentSerializer(top, many=True, context=self.context).data

    def get_poll(self, obj):
        try:
            return PollSerializer(obj.poll, context=self.context).data
        except Poll.DoesNotExist:
            return None

    def get_link_preview(self, obj):
        try:
            lp = obj.link_preview
            if lp:
                return {
                    'url': lp.url,
                    'title': lp.title,
                    'description': lp.description,
                    'image': lp.image,
                    'domain': lp.domain,
                }
        except Exception:
            pass
        return None
