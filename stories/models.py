from django.db import models
from django.utils import timezone
from datetime import timedelta
from users.models import User


def story_expires():
    return timezone.now() + timedelta(hours=24)


class Story(models.Model):
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('text', 'Text'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    media_url = models.URLField(blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, default='image')
    text_content = models.TextField(max_length=500, blank=True)
    text_color = models.CharField(max_length=7, default='#ffffff')
    bg_color = models.CharField(max_length=7, default='#6c63ff')
    caption = models.CharField(max_length=250, blank=True)
    expires_at = models.DateTimeField(default=story_expires)
    created_at = models.DateTimeField(auto_now_add=True)
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']

    def is_active(self):
        return timezone.now() < self.expires_at

    def __str__(self):
        return f"Story by {self.author.username} at {self.created_at}"


class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='story_views')
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewed_stories')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['story', 'viewer']


class StoryReaction(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['story', 'user']


class StoryHighlight(models.Model):
    """Pinned story collections on a user's profile."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='highlights')
    title = models.CharField(max_length=30)
    cover_story = models.ForeignKey(
        Story, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    stories = models.ManyToManyField(Story, related_name='highlights', blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.owner.username} - {self.title}"
