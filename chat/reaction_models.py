from django.db import models
from users.models import User


class MessageReaction(models.Model):
    """Emoji reactions on chat messages."""
    from chat.models import Message
    message = models.ForeignKey('chat.Message', on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions')
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user', 'emoji']
        indexes = [models.Index(fields=['message'])]

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to msg {self.message_id}"


class PinnedMessage(models.Model):
    room = models.ForeignKey('chat.Room', on_delete=models.CASCADE, related_name='pinned_messages')
    message = models.ForeignKey('chat.Message', on_delete=models.CASCADE, related_name='pinned_in')
    pinned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    pinned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['room', 'message']
