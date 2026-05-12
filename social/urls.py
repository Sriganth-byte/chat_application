from django.urls import path
from . import views

urlpatterns = [
    path('profile/<str:username>/', views.UserProfileView.as_view(), name='user-profile'),
    path('friend-request/', views.FriendRequestView.as_view(), name='send-friend-request'),
    path('friend-request/<int:pk>/', views.FriendRequestActionView.as_view(), name='friend-request-action'),
    path('friend-requests/', views.FriendRequestListView.as_view(), name='friend-request-list'),
    path('friends/', views.FriendListView.as_view(), name='friend-list'),
    path('friends/<int:user_id>/', views.UnfriendView.as_view(), name='unfriend'),
    path('follow/<int:user_id>/', views.FollowView.as_view(), name='follow'),
    path('suggestions/', views.UserSuggestionsView.as_view(), name='user-suggestions'),
]
