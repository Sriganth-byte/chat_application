from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model extending AbstractUser.
    Adds profile fields, presence tracking, and multi-device sessions.
    """
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        default='avatars/default.png'
    )
    # Stores URL from external upload (chat upload / Supabase) — takes priority over avatar file
    avatar_url_field = models.URLField(max_length=1000, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, default='')
    last_seen = models.DateTimeField(null=True, blank=True, db_index=True)
    is_online = models.BooleanField(default=False, db_index=True)
    active_sessions = models.JSONField(
        default=list, blank=True,
        help_text="List of active session IDs for this user"
    )
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(
        max_length=100, blank=True, null=True, unique=True
    )
    preferences = models.JSONField(default=dict, blank=True)
    blocked_users = models.ManyToManyField(
        'self', symmetrical=False, related_name='blocked_by', blank=True
    )
    # Trust & Verification
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['is_online', 'last_seen']),
            models.Index(fields=['is_verified']),
        ]
        ordering = ['-date_joined']

    def __str__(self):
        return self.username

    def add_session(self, session_id):
        if not self.active_sessions:
            self.active_sessions = []
        if session_id not in self.active_sessions:
            self.active_sessions.append(session_id)
            self.is_online = True
            self.last_seen = timezone.now()
            self.save(update_fields=['active_sessions', 'is_online', 'last_seen'])

    def remove_session(self, session_id):
        if session_id in self.active_sessions:
            self.active_sessions.remove(session_id)
            self.is_online = len(self.active_sessions) > 0
            if not self.is_online:
                self.last_seen = timezone.now()
            self.save(update_fields=['active_sessions', 'is_online', 'last_seen'])


class UserLoginHistory(models.Model):
    """Track login attempts and device sessions for security."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(
        max_length=20,
        choices=[('mobile', 'Mobile'), ('tablet', 'Tablet'), ('desktop', 'Desktop'), ('unknown', 'Unknown')],
        default='unknown'
    )
    os_family = models.CharField(max_length=50, blank=True)
    browser_family = models.CharField(max_length=50, blank=True)
    session_key = models.CharField(max_length=100, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    is_suspicious = models.BooleanField(default=False)
    logged_in_at = models.DateTimeField(auto_now_add=True, db_index=True)
    logged_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-logged_in_at']
        indexes = [models.Index(fields=['user', '-logged_in_at'])]

    def __str__(self):
        return f"{self.user.username} from {self.ip_address} ({self.device_type})"


class WebPushSubscription(models.Model):
    """Store browser push notification subscriptions."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Push sub for {self.user.username}"


class FeatureFlag(models.Model):
    """Feature flags for gradual rollout and A/B testing."""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=False)
    rollout_percentage = models.PositiveSmallIntegerField(
        default=100,
        help_text="Percentage of users (0-100) who see this feature"
    )
    allowed_users = models.ManyToManyField(User, blank=True, related_name='feature_flags')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({'ON' if self.is_enabled else 'OFF'})"

    def is_active_for(self, user):
        """Check if flag is active for a given user."""
        if not self.is_enabled:
            return False
        if self.allowed_users.filter(id=user.id).exists():
            return True
        if self.rollout_percentage >= 100:
            return True
        # Deterministic hash-based rollout
        import hashlib
        h = int(hashlib.md5(f"{self.name}:{user.id}".encode()).hexdigest(), 16)
        return (h % 100) < self.rollout_percentage



