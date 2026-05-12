"""
Chat service for MindConnect.
Handles messaging, room management, and real-time operations.
"""
from typing import Optional, List, Dict, Any
from django.db import transaction
from django.utils import timezone
from ..services.base import ServiceBase, ServiceResult, ErrorCode
from chat.models import Room, RoomMember, Message, MessageReaction
from users.models import User


class ChatService(ServiceBase):
    """Service for chat operations."""
    
    def get_or_create_dm_room(self, user1: User, user2: User) -> ServiceResult[Room]:
        """Get or create a direct message room between two users."""
        try:
            with transaction.atomic():
                # Look for existing DM room with both users
                rooms = Room.objects.filter(type='dm')
                
                for room in rooms:
                    member_ids = list(room.members.values_list('user_id', flat=True))
                    if set(member_ids) == {user1.id, user2.id}:
                        return self._result_ok(room)
                
                # Create new room
                room = Room.objects.create(
                    type='dm',
                    created_by=user1,
                    name=f'{user1.username} & {user2.username}'
                )
                RoomMember.objects.create(room=room, user=user1)
                RoomMember.objects.create(room=room, user=user2)
                
                return self._result_ok(room)
        except Exception as e:
            return self._result_fail(
                f'Failed to create DM room: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )
    
    def create_group_room(
        self,
        name: str,
        created_by: User,
        member_ids: List[int],
        description: str = ''
    ) -> ServiceResult[Room]:
        """Create a new group room."""
        try:
            with transaction.atomic():
                room = Room.objects.create(
                    type='group',
                    name=name,
                    description=description,
                    created_by=created_by
                )
                
                # Add creator as admin
                RoomMember.objects.create(
                    room=room,
                    user=created_by,
                    role='admin'
                )
                
                # Add other members
                for member_id in member_ids:
                    if member_id != created_by.id:
                        RoomMember.objects.create(
                            room=room,
                            user_id=member_id
                        )
                
                return self._result_ok(room)
        except Exception as e:
            return self._result_fail(
                f'Failed to create group room: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )
    
    def send_message(
        self,
        room_id: int,
        sender: User,
        content: str,
        message_type: str = 'text',
        reply_to_id: Optional[int] = None,
        file_url: Optional[str] = None
    ) -> ServiceResult[Message]:
        """Send a message to a room."""
        try:
            # Verify room membership
            if not RoomMember.objects.filter(
                room_id=room_id,
                user_id=sender.id
            ).exists():
                return self._result_fail(
                    'Not a member of this room',
                    ErrorCode.PERMISSION_DENIED
                )
            
            # Validate content for text messages
            if message_type == 'text' and not content.strip():
                return self._result_fail(
                    'Message content cannot be empty',
                    ErrorCode.VALIDATION_ERROR
                )
            
            message = Message.objects.create(
                room_id=room_id,
                sender=sender,
                content=content,
                message_type=message_type,
                reply_to_id=reply_to_id,
                file_url=file_url
            )
            
            return self._result_ok(message)
        except Exception as e:
            return self._result_fail(
                f'Failed to send message: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )
    
    def edit_message(
        self,
        message_id: int,
        user: User,
        new_content: str
    ) -> ServiceResult[Message]:
        """Edit a message (only sender can edit)."""
        try:
            updated = Message.objects.filter(
                id=message_id,
                sender=user
            ).update(
                content=new_content,
                edited=True,
                edited_at=timezone.now()
            )
            
            if not updated:
                return self._result_fail(
                    'Message not found or not authorized',
                    ErrorCode.NOT_FOUND
                )
            
            message = Message.objects.select_related('sender').get(id=message_id)
            return self._result_ok(message)
        except Exception as e:
            return self._result_fail(
                f'Failed to edit message: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )
    
    def delete_message(self, message_id: int, user: User) -> ServiceResult[None]:
        """Delete a message (only sender can delete)."""
        try:
            deleted, _ = Message.objects.filter(
                id=message_id,
                sender=user
            ).delete()
            
            if not deleted:
                return self._result_fail(
                    'Message not found or not authorized',
                    ErrorCode.NOT_FOUND
                )
            
            return self._result_ok()
        except Exception as e:
            return self._result_fail(
                f'Failed to delete message: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )
    
    def add_reaction(
        self,
        message_id: int,
        user: User,
        emoji: str
    ) -> ServiceResult[MessageReaction]:
        """Add emoji reaction to a message."""
        try:
            reaction, _ = MessageReaction.objects.get_or_create(
                message_id=message_id,
                user=user,
                emoji=emoji
            )
            return self._result_ok(reaction)
        except Exception as e:
            return self._result_fail(
                f'Failed to add reaction: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )
    
    def mark_messages_seen(
        self,
        message_ids: List[int],
        user: User
    ) -> ServiceResult[int]:
        """Mark messages as seen by user."""
        try:
            messages = Message.objects.filter(id__in=message_ids)
            for message in messages:
                message.seen_by.add(user)
            Message.objects.filter(id__in=message_ids).update(is_seen=True)
            return self._result_ok(len(message_ids))
        except Exception as e:
            return self._result_fail(
                f'Failed to mark messages seen: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )
    
    def get_room_messages(
        self,
        room_id: int,
        user: User,
        limit: int = 50,
        offset: int = 0
    ) -> ServiceResult[List[Message]]:
        """Get recent messages for a room."""
        try:
            # Verify membership
            if not RoomMember.objects.filter(
                room_id=room_id,
                user_id=user.id
            ).exists():
                return self._result_fail(
                    'Not a member of this room',
                    ErrorCode.PERMISSION_DENIED
                )
            
            messages = Message.objects.filter(
                room_id=room_id
            ).select_related(
                'sender', 'reply_to__sender'
            ).order_by('-created_at')[offset:offset + limit]
            
            return self._result_ok(list(messages))
        except Exception as e:
            return self._result_fail(
                f'Failed to get messages: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )