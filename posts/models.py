from django.db import models
from users.models import User


class Post(models.Model):
    """Main post/feed content."""
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]
    STATUS_CHOICES = [
        ('published', 'Published'),
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(max_length=5000, blank=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='published', db_index=True)
    publish_at = models.DateTimeField(null=True, blank=True, db_index=True, help_text="For scheduled posts")
    media = models.JSONField(default=list, blank=True, help_text="List of media URLs")
    media_type = models.CharField(
        max_length=10,
        choices=[('none', 'None'), ('image', 'Image'), ('video', 'Video'), ('audio', 'Audio')],
        default='none'
    )
    hashtags = models.JSONField(default=list, blank=True)
    mentions = models.ManyToManyField(User, related_name='mentioned_in', blank=True)
    shared_post = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reposts'
    )
    link_preview = models.JSONField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Counters (denormalized for performance)
    likes_count = models.PositiveIntegerField(default=0, db_index=True)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    impressions_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['visibility', 'status', '-created_at']),
            models.Index(fields=['status', 'publish_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author.username}: {self.content[:50]}"


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liked_posts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']
        indexes = [models.Index(fields=['post', 'user'])]


class PostComment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField(max_length=2000)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies'
    )
    likes_count = models.PositiveIntegerField(default=0)
    edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['post', 'created_at'])]

    def __str__(self):
        return f"{self.author.username} on post {self.post_id}"


class CommentLike(models.Model):
    comment = models.ForeignKey(PostComment, on_delete=models.CASCADE, related_name='comment_likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['comment', 'user']


class PostShare(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_posts')
    caption = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']


class PostSave(models.Model):
    """Saved/bookmarked posts, optionally in a collection."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saves')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_posts')
    collection = models.ForeignKey(
        'SavedCollection', on_delete=models.SET_NULL, null=True, blank=True, related_name='items'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']


class SavedCollection(models.Model):
    """Named folder for organizing saved posts."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_collections')
    name = models.CharField(max_length=100)
    emoji = models.CharField(max_length=10, blank=True, default='🔖')
    is_private = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['owner', 'name']

    def __str__(self):
        return f"{self.owner.username} / {self.name}"


class PostAnalytics(models.Model):
    """Daily analytics snapshot per post."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(db_index=True)
    views = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    saves = models.PositiveIntegerField(default=0)
    reach = models.PositiveIntegerField(default=0, help_text="Unique users who saw this")

    class Meta:
        unique_together = ['post', 'date']
        ordering = ['-date']


class Poll(models.Model):
    """Poll attached to a post."""
    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name='poll')
    question = models.CharField(max_length=300)
    closes_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

    def total_votes(self):
        return sum(opt.votes.count() for opt in self.options.all())


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']


class PollVote(models.Model):
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='poll_votes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        pass

    def save(self, *args, **kwargs):
        PollVote.objects.filter(option__poll=self.option.poll, voter=self.voter).exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)
