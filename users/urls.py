from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, ProfileView,
    ForgotPasswordView, ResetPasswordView, CustomTokenRefreshView,
    UserListView, UserDetailView, ChangePasswordView,
)
from .gdpr_views import DataExportView, DeleteAccountView
from .health import HealthCheckView
from .totp_views import TOTPSetupView, TOTPVerifyView, TOTPDisableView
from .platform_views import (
    PushSubscribeView, SessionListView, SessionRevokeView, SessionRevokeAllView,
    FeatureFlagsView, VerifyUserView, AuditLogView
)
from .analytics_views import ProfileAnalyticsView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/verify/', VerifyUserView.as_view(), name='user-verify'),
    # GDPR
    path('export-data/', DataExportView.as_view(), name='export-data'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    # 2FA / TOTP
    path('2fa/setup/', TOTPSetupView.as_view(), name='totp-setup'),
    path('2fa/verify/', TOTPVerifyView.as_view(), name='totp-verify'),
    path('2fa/disable/', TOTPDisableView.as_view(), name='totp-disable'),
    # Push notifications
    path('push/subscribe/', PushSubscribeView.as_view(), name='push-subscribe'),
    # Sessions
    path('sessions/', SessionListView.as_view(), name='session-list'),
    path('sessions/all/', SessionRevokeAllView.as_view(), name='session-revoke-all'),
    path('sessions/<int:pk>/', SessionRevokeView.as_view(), name='session-revoke'),
    # Feature flags
    path('features/', FeatureFlagsView.as_view(), name='feature-flags'),
    # Analytics
    path('analytics/', ProfileAnalyticsView.as_view(), name='profile-analytics'),
    # Audit log (admin)
    path('audit-log/', AuditLogView.as_view(), name='audit-log'),
]
