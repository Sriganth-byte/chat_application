"""
Custom permission classes for the application.
"""
from rest_framework import permissions


class IsRoomMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the room.
    """

    def has_object_permission(self, request, view, obj):
        # For Room objects
        if hasattr(obj, 'members'):
            return obj.members.filter(user=request.user).exists()
        # For Message objects (check via room)
        if hasattr(obj, 'room'):
            return obj.room.members.filter(user=request.user).exists()
        return False


class IsRoomAdmin(permissions.BasePermission):
    """
    Permission to check if user is admin of the room.
    """

    def has_object_permission(self, request, view, obj):
        from chat.models import RoomMember
        try:
            membership = RoomMember.objects.get(room=obj, user=request.user)
            return membership.role == 'admin'
        except RoomMember.DoesNotExist:
            return False


class IsMessageOwner(permissions.BasePermission):
    """
    Permission to check if user owns the message.
    """

    def has_object_permission(self, request, view, obj):
        return obj.sender == request.user
