from django.urls import path
from . import views
from .link_preview import LinkPreviewView
from .share_views import PostShareView, RepostView
from .analytics_views import PostAnalyticsView

urlpatterns = [
    path('feed/', views.FeedView.as_view(), name='post-feed'),
    path('', views.PostCreateView.as_view(), name='post-create'),
    path('<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('<int:pk>/like/', views.PostLikeView.as_view(), name='post-like'),
    path('<int:pk>/save/', views.PostSaveView.as_view(), name='post-save'),
    path('<int:pk>/share/', PostShareView.as_view(), name='post-share'),
    path('<int:pk>/repost/', RepostView.as_view(), name='post-repost'),
    path('<int:pk>/comments/', views.PostCommentListView.as_view(), name='post-comments'),
    path('<int:pk>/poll/vote/', views.PollVoteView.as_view(), name='poll-vote'),
    path('<int:pk>/analytics/', PostAnalyticsView.as_view(), name='post-analytics'),
    path('comments/<int:pk>/', views.CommentDetailView.as_view(), name='comment-detail'),
    path('comments/<int:pk>/like/', views.CommentLikeView.as_view(), name='comment-like'),
    path('saved/', views.SavedPostsView.as_view(), name='saved-posts'),
    path('saved/collections/', views.SavedCollectionsView.as_view(), name='saved-collections'),
    path('user/<str:username>/', views.UserPostsView.as_view(), name='user-posts'),
    path('trending/', views.TrendingHashtagsView.as_view(), name='trending-hashtags'),
    path('hashtag/<str:tag>/', views.HashtagFeedView.as_view(), name='hashtag-feed'),
    path('link-preview/', LinkPreviewView.as_view(), name='link-preview'),
    path('scheduled/', views.ScheduledPostsView.as_view(), name='scheduled-posts'),
]
