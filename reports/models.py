from django.db import models
from users.models import User


class Report(models.Model):
    TARGET_TYPES = [
        ('post', 'Post'),
        ('comment', 'Comment'),
        ('message', 'Message'),
        ('user', 'User'),
        ('story', 'Story'),
        ('room', 'Room'),
    ]
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment / Bullying'),
        ('hate_speech', 'Hate Speech'),
        ('violence', 'Violence or Threats'),
        ('misinformation', 'Misinformation'),
        ('adult_content', 'Inappropriate / Adult Content'),
        ('copyright', 'Copyright Violation'),
        ('impersonation', 'Impersonation'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewing', 'Under Review'),
        ('resolved_action', 'Resolved — Action Taken'),
        ('resolved_dismissed', 'Resolved — Dismissed'),
    ]

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filed_reports')
    target_type = models.CharField(max_length=10, choices=TARGET_TYPES)
    target_id = models.PositiveBigIntegerField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_reports'
    )
    reviewer_note = models.TextField(blank=True)
    auto_flagged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['reporter']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Report by {self.reporter.username}: {self.target_type}#{self.target_id} ({self.status})"


class AuditLog(models.Model):
    """Immutable log of all admin/moderation actions."""
    ACTION_TYPES = [
        ('ban_user', 'Banned User'),
        ('unban_user', 'Unbanned User'),
        ('verify_user', 'Verified User'),
        ('unverify_user', 'Removed Verification'),
        ('delete_post', 'Deleted Post'),
        ('delete_message', 'Deleted Message'),
        ('delete_story', 'Deleted Story'),
        ('resolve_report', 'Resolved Report'),
        ('dismiss_report', 'Dismissed Report'),
        ('warn_user', 'Warned User'),
        ('force_logout', 'Force Logged Out User'),
        ('promote_admin', 'Promoted to Admin'),
        ('impersonate', 'Impersonated User'),
        ('export_data', 'Exported User Data'),
        ('delete_account', 'Deleted Account'),
        ('flag_content', 'AI-Flagged Content'),
    ]
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_actions')
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    target_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_targets'
    )
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.PositiveBigIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.actor} — {self.action} at {self.created_at}"
