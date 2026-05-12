"""
User repository for data access.
"""
from typing import Optional, List
from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from .base import RepositoryBase

User = get_user_model()


class UserRepository(RepositoryBase[User]):
    """Repository for User model operations."""
    
    model_class = User
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            return self.model_class.objects.get(email=email)
        except self.model_class.DoesNotExist:
            return None
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            return self.model_class.objects.get(username=username)
        except self.model_class.DoesNotExist:
            return None
    
    def search(self, query: str, exclude_user_id: Optional[int] = None) -> QuerySet[User]:
        """Search users by username or email."""
        qs = self.model_class.objects.exclude(id=exclude_user_id) if exclude_user_id else self.model_class.objects.all()
        from django.db.models import Q
        return qs.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        )
    
    def get_online_users(self) -> QuerySet[User]:
        """Get all online users."""
        return self.model_class.objects.filter(is_online=True)
    
    def set_online(self, user_id: int, is_online: bool) -> int:
        """Set user online status."""
        return self.model_class.objects.filter(id=user_id).update(
            is_online=is_online,
            last_seen=None if is_online else self.model_class.objects.model.last_seen.field.default
        )