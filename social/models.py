from django.db import models
from django.utils import timezone
from users.models import User


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['sender', 'receiver']
        indexes = [
            models.Index(fields=['receiver', 'status']),
            models.Index(fields=['sender', 'status']),
        ]

    def __str__(self):
        return f"{self.sender} → {self.receiver} ({self.status})"


class Friendship(models.Model):
    """Bidirectional friendship record created when request is accepted."""
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user1', 'user2']
        indexes = [models.Index(fields=['user1']), models.Index(fields=['user2'])]

    def __str__(self):
        return f"{self.user1} ↔ {self.user2}"

    @classmethod
    def are_friends(cls, user_a, user_b):
        u1, u2 = (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)
        return cls.objects.filter(user1=u1, user2=u2).exists()

    @classmethod
    def get_friends(cls, user):
        from django.db.models import Q
        ids = cls.objects.filter(Q(user1=user) | Q(user2=user)).values_list('user1_id', 'user2_id')
        friend_ids = set()
        for u1, u2 in ids:
            friend_ids.add(u2 if u1 == user.id else u1)
        return User.objects.filter(id__in=friend_ids)


class Follow(models.Model):
    """One-directional follow (for public profiles)."""
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['follower', 'following']
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['following']),
        ]

    def __str__(self):
        return f"{self.follower} follows {self.following}"



class UserProfile(models.Model):
    """Extended profile data."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    cover_photo = models.ImageField(upload_to='covers/', null=True, blank=True)
    is_private = models.BooleanField(default=False)
    show_online_status = models.BooleanField(default=True)
    allow_messages_from = models.CharField(
        max_length=10,
        choices=[('everyone', 'Everyone'), ('friends', 'Friends Only'), ('none', 'No One')],
        default='everyone'
    )
    theme = models.CharField(
        max_length=10,
        choices=[('dark', 'Dark'), ('light', 'Light'), ('auto', 'Auto')],
        default='dark'
    )
    # 2FA / TOTP
    totp_secret = models.CharField(max_length=64, blank=True)
    totp_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.username}"
