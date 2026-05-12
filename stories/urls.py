from django.urls import path
from . import views
from .highlight_views import StoryHighlightListView, StoryHighlightDetailView, StoryHighlightCreateView

urlpatterns = [
    path('', views.StoryListView.as_view(), name='story-list'),
    path('create/', views.StoryCreateView.as_view(), name='story-create'),
    path('<int:pk>/view/', views.StoryViewView.as_view(), name='story-view'),
    path('<int:pk>/', views.StoryDeleteView.as_view(), name='story-delete'),
    # Highlights
    path('highlights/create/', StoryHighlightCreateView.as_view(), name='highlight-create'),
    path('highlights/<str:username>/', StoryHighlightListView.as_view(), name='highlight-list'),
    path('highlights/detail/<int:pk>/', StoryHighlightDetailView.as_view(), name='highlight-detail'),
]
