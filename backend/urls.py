"""
URL configuration for backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from users.health import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/chat/', include('chat.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/social/', include('social.urls')),
    path('api/posts/', include('posts.urls')),
    path('api/stories/', include('stories.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/admin-dashboard/', include('admin_dashboard.urls')),
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    # Replace the default django.views.static.serve with a Range-aware view.
    # Browsers REQUIRE HTTP 206 Partial Content (Range support) to play video
    # and audio files. Django's built-in serve always returns 200, which causes
    # Chrome/Safari to refuse to play media entirely.
    from django.urls import re_path
    from backend.utils.range_serve import serve_media_with_range
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media_with_range),
    ]
