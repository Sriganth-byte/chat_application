from django.db import models
from django.db.models import Q
from django.utils import timezone
from users.models import User


class RoomManager(models.Manager):
    """Custom manager for Room model with DM creation."""
    
    def get_or_create_dm(self, user1, user2):
        """Get or create a direct message room between two users."""
        # Look for existing DM room with both users
        from django.db.models import Count
        rooms = self.filter(type='dm')
        
        for room in rooms.prefetch_related('members'):
            member_ids = set(room.members.values_list('user_id', flat=True))
            if member_ids == {user1.id, user2.id}:
                return room, False
        
        # Create new DM room
        room = self.create(
            type='dm',
            created_by=user1,
            name=f'{user1.username} & {user2.username}'
        )
        RoomMember.objects.create(room=room, user=user1)
        RoomMember.objects.create(room=room, user=user2)
        
        return room, True


class Room(models.Model):
    """Chat room model for both Direct Messages and Group chats."""
    ROOM_TYPES = [
        ('dm', 'Direct Message'),
        ('group', 'Group'),
    ]

    name = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=10, choices=ROOM_TYPES)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_rooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    avatar = models.ImageField(
        upload_to='room_avatars/',
        null=True,
        blank=True
    )
    description = models.TextField(
        max_length=1000,
        blank=True,
        default=''
    )
    admins = models.ManyToManyField(
        User,
        related_name='admin_rooms',
        blank=True
    )
    
    objects = RoomManager()

    class Meta:
        indexes = [
            models.Index(fields=['type', 'created_at']),
            models.Index(fields=['created_by']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.name or f"Room {self.id}"

    def get_member_count(self):
        return self.members.count()


class RoomMember(models.Model):
    """
    Membership model linking users to rooms with role information.
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rooms'
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='member'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['room', 'user']
        indexes = [
            models.Index(fields=['room', 'user']),
            models.Index(fields=['user', 'joined_at']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.room}"


class Message(models.Model):
    """
    Message model supporting text, images, files, audio, video.
    """
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('audio', 'Audio'),
        ('video', 'Video'),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPES,
        default='text'
    )
    content = models.TextField()
    file_url = models.URLField(null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    one_time = models.BooleanField(default=False)
    one_time_read_by = models.ManyToManyField(
        User,
        related_name='one_time_messages',
        blank=True
    )
    is_seen = models.BooleanField(default=False)
    seen_by = models.ManyToManyField(
        User,
        related_name='seen_messages',
        blank=True
    )
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['room', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender}: {self.content[:50]}"


class MessageReaction(models.Model):
    """Emoji reactions on messages."""
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='reactions'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='message_reactions'
    )
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user', 'emoji']
        indexes = [models.Index(fields=['message'])]

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to msg {self.message_id}"


class PinnedMessage(models.Model):
    """Pinned messages per room."""
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='pinned_messages'
    )
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='pinned_in'
    )
    pinned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    pinned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['room', 'message']

    def __str__(self):
        return f"Pinned msg {self.message_id} in {self.room}"
