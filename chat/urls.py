from django.urls import path
from .views import (
    RoomListView, RoomDetailView,
    RoomMemberView, RoomMemberDetailView, LeaveRoomView,
    MessageListView, SendMessageView, MessageDetailView,
    MessageConsumeView, SearchView, MessageReactionView,
)
from .upload import FileUploadView

urlpatterns = [
    # Rooms
    path('rooms/', RoomListView.as_view(), name='room-list'),
    path('rooms/<int:pk>/', RoomDetailView.as_view(), name='room-detail'),

    # Group member management
    path('rooms/<int:pk>/members/', RoomMemberView.as_view(), name='room-members'),
    path('rooms/<int:pk>/members/<int:user_id>/', RoomMemberDetailView.as_view(), name='room-member-detail'),
    path('rooms/<int:pk>/leave/', LeaveRoomView.as_view(), name='room-leave'),

    # Messages
    path('rooms/<int:room_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('rooms/<int:room_id>/send/', SendMessageView.as_view(), name='send-message'),
    path('messages/<int:message_id>/', MessageDetailView.as_view(), name='message-detail'),
    path('messages/<int:message_id>/consume/', MessageConsumeView.as_view(), name='message-consume'),

    # File upload
    path('upload/', FileUploadView.as_view(), name='file-upload'),

    # Message reactions
    path('messages/<int:message_id>/react/', MessageReactionView.as_view(), name='message-react'),

    # Search
    path('search/', SearchView.as_view(), name='search'),
]
