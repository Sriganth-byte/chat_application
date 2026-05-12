from django.db import models
from users.models import User


class Notification(models.Model):
    """
    Notification model for real-time and email notifications.
    """
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('mention', 'Mention'),
        ('group_invite', 'Group Invitation'),
        ('message_seen', 'Message Seen'),
        ('friend_request', 'Friend Request'),
        ('friend_accepted', 'Friend Request Accepted'),
        ('new_follower', 'New Follower'),
        ('post_like', 'Post Liked'),
        ('post_comment', 'Post Commented'),
        ('story_reaction', 'Story Reaction'),
        ('system', 'System Announcement'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context data"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_read', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} for {self.user.username}"
