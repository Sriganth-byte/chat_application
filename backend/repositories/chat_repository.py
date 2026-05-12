"""
Chat repository for data access.
"""
from typing import Optional, List
from django.db.models import QuerySet

from .base import RepositoryBase
from chat.models import Room, RoomMember, Message, MessageReaction


class MessageRepository(RepositoryBase[Message]):
    """Repository for Message model operations."""
    
    model_class = Message
    
    def get_room_messages(
        self,
        room_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> QuerySet[Message]:
        """Get messages for a room with pagination."""
        return self.model_class.objects.filter(
            room_id=room_id
        ).select_related(
            'sender', 'reply_to__sender'
        ).order_by('-created_at')[offset:offset + limit]
    
    def get_unseen_messages(
        self,
        room_id: int,
        user_id: int
    ) -> QuerySet[Message]:
        """Get messages not seen by user."""
        return self.model_class.objects.filter(
            room_id=room_id
        ).exclude(
            seen_by=user_id
        ).exclude(
            sender_id=user_id
        )


class RoomRepository(RepositoryBase[Room]):
    """Repository for Room model operations."""
    
    model_class = Room
    
    def get_user_rooms(self, user_id: int) -> QuerySet[Room]:
        """Get all rooms for a user."""
        return self.model_class.objects.filter(
            members__user_id=user_id
        ).prefetch_related(
            'members__user'
        ).distinct()
    
    def get_dm_room(self, user1_id: int, user2_id: int) -> Optional[Room]:
        """Get existing DM room between two users."""
        rooms = self.model_class.objects.filter(
            type='dm'
        ).prefetch_related('members')
        
        for room in rooms:
            member_ids = set(room.members.values_list('user_id', flat=True))
            if member_ids == {user1_id, user2_id}:
                return room
        return None


class RoomMemberRepository(RepositoryBase[RoomMember]):
    """Repository for RoomMember model operations."""
    
    model_class = RoomMember
    
    def is_member(self, room_id: int, user_id: int) -> bool:
        """Check if user is member of room."""
        return self.model_class.objects.filter(
            room_id=room_id,
            user_id=user_id
        ).exists()
    
    def get_members(self, room_id: int) -> QuerySet[RoomMember]:
        """Get all members of a room."""
        return self.model_class.objects.filter(
            room_id=room_id
        ).select_related('user')
    
    def update_last_read(self, room_id: int, user_id: int) -> int:
        """Update user's last read timestamp."""
        from django.utils import timezone
        return self.model_class.objects.filter(
            room_id=room_id,
            user_id=user_id
        ).update(last_read=timezone.now())