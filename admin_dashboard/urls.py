from django.urls import path

from .views import (
    AdminAuditLogView,
    AdminDashboardView,
    AdminPostDetailView,
    AdminPostListView,
    AdminReportDetailView,
    AdminReportListView,
    AdminUserDetailView,
    AdminUserListView,
)


urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard-api'),
    path('users/', AdminUserListView.as_view(), name='admin-users'),
    path('users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('posts/', AdminPostListView.as_view(), name='admin-posts'),
    path('posts/<int:pk>/', AdminPostDetailView.as_view(), name='admin-post-detail'),
    path('reports/', AdminReportListView.as_view(), name='admin-reports'),
    path('reports/<int:pk>/', AdminReportDetailView.as_view(), name='admin-report-detail'),
    path('audit/', AdminAuditLogView.as_view(), name='admin-audit'),
]
