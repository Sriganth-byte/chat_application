from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import (
    OutstandingToken,
    BlacklistedToken
)
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError
from django.contrib.auth import get_user_model, logout
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import secrets

from .serializers import (
    UserSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer
)

User = get_user_model()


from django.http import JsonResponse


def ratelimited(request, exception):
    """Custom rate limit response view"""
    return JsonResponse(
        {'detail': 'Rate limit exceeded. Please try again later.'},
        status=429
    )


class UserListView(generics.ListAPIView):
    """GET /api/users — search/list users"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = None

    def get_queryset(self):
        qs = User.objects.exclude(id=self.request.user.id)
        q = self.request.query_params.get('q', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
        return qs


class UserDetailView(generics.RetrieveAPIView):
    """GET /api/users/{id} — get user profile by ID"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()


@method_decorator(ratelimit(key='ip', rate='200/hour', block=True), name='dispatch')
class RegisterView(APIView):
    """User registration endpoint"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response(
                    UserSerializer(user).data,
                    status=status.HTTP_201_CREATED
                )
            except IntegrityError:
                return Response(
                    {"error": "Username or email already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='ip', rate='100/minute', block=True), name='dispatch')
class LoginView(APIView):
    """Custom login with JWT tokens - accepts email or username"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken

        email_or_username = request.data.get('email') or request.data.get('username', '')
        password = request.data.get('password', '')

        if not email_or_username or not password:
            return Response({'detail': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)

        # Try to find user by email or username
        try:
            if '@' in email_or_username:
                user = User.objects.get(email=email_or_username)
            else:
                user = User.objects.get(username=email_or_username)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # Create tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # Add custom claims to access token
        access['username'] = user.username
        access['email'] = user.email
        if user.avatar and hasattr(user.avatar, 'url'):
            access['avatar'] = user.avatar.url
        access['is_online'] = user.is_online

        # Track user session for presence
        session_id = secrets.token_urlsafe(32)
        user.add_session(session_id)

        # ── Record login history (real session tracking) ──────────────────────
        try:
            from .models import UserLoginHistory
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            ua_string = request.META.get('HTTP_USER_AGENT', '')

            # Parse device/browser info from User-Agent
            device_type = 'desktop'
            browser_family = 'Unknown'
            os_family = 'Unknown'
            try:
                from user_agents import parse as ua_parse
                ua = ua_parse(ua_string)
                browser_family = ua.browser.family
                os_family = ua.os.family
                if ua.is_mobile:
                    device_type = 'mobile'
                elif ua.is_tablet:
                    device_type = 'tablet'
            except Exception:
                # user-agents lib not installed — basic detection
                ua_lower = ua_string.lower()
                if any(x in ua_lower for x in ['iphone', 'android', 'mobile']):
                    device_type = 'mobile'
                elif 'tablet' in ua_lower or 'ipad' in ua_lower:
                    device_type = 'tablet'
                if 'chrome' in ua_lower:
                    browser_family = 'Chrome'
                elif 'firefox' in ua_lower:
                    browser_family = 'Firefox'
                elif 'safari' in ua_lower:
                    browser_family = 'Safari'
                if 'windows' in ua_lower:
                    os_family = 'Windows'
                elif 'mac' in ua_lower:
                    os_family = 'macOS'
                elif 'linux' in ua_lower:
                    os_family = 'Linux'
                elif 'android' in ua_lower:
                    os_family = 'Android'
                elif 'iphone' in ua_lower or 'ipad' in ua_lower:
                    os_family = 'iOS'

            login_record = UserLoginHistory.objects.create(
                user=user,
                ip_address=ip,
                user_agent=ua_string[:500],
                device_type=device_type,
                browser_family=browser_family,
                os_family=os_family,
                session_key=session_id,
                is_active=True,
            )

            # Async suspicious login check
            try:
                from .tasks import check_suspicious_login
                check_suspicious_login.delay(login_record.id)
            except Exception:
                pass

        except Exception:
            pass  # Never break login over tracking failure

        return Response({
            'refresh': str(refresh),
            'access': str(access),
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """Logout and invalidate all tokens"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Blacklist all user tokens
            tokens = OutstandingToken.objects.filter(user=request.user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)

            # Clear user sessions
            request.user.active_sessions = []
            request.user.is_online = False
            request.user.last_seen = timezone.now()
            request.user.save(update_fields=['active_sessions', 'is_online', 'last_seen'])

            return Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(APIView):
    """Get and update user profile"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        """Update profile"""
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Change the current user's password after validating their current password."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password', '')
        new_password = request.data.get('new_password', '')

        if not request.user.check_password(current_password):
            return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return Response({'error': 'New password is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, request.user)
        except ValidationError as exc:
            return Response({'error': ' '.join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        return Response({'message': 'Password changed successfully'})


@method_decorator(ratelimit(key='ip', rate='50/hour', block=True), name='dispatch')
class ForgotPasswordView(APIView):
    """Request password reset link"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                user.verification_token = secrets.token_urlsafe(32)
                user.save(update_fields=['verification_token'])

                reset_url = f"{settings.FRONTEND_URL}/reset-password?token={user.verification_token}"
                send_mail(
                    subject='Reset Your MindConnect Password',
                    message=f'Click the link to reset your password: {reset_url}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except User.DoesNotExist:
                pass

            return Response(
                {"message": "If the email exists, a reset link has been sent"},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='ip', rate='50/hour', block=True), name='dispatch')
class ResetPasswordView(APIView):
    """Reset password with token"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(verification_token=token)
                user.set_password(new_password)
                user.verification_token = None
                user.save(update_fields=['password', 'verification_token'])

                return Response(
                    {"message": "Password reset successfully"},
                    status=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid or expired token"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    """Token refresh endpoint"""
    pass
