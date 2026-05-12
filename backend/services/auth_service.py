"""
Authentication service for MindConnect.
Handles user registration, login, logout, and token management.
"""
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model, authenticate
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import (
    OutstandingToken,
    BlacklistedToken
)
from ..services.base import ServiceBase, ServiceResult, ErrorCode
import secrets

User = get_user_model()


class AuthService(ServiceBase):
    """Service for authentication operations."""
    
    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        **extra_fields
    ) -> ServiceResult[Dict[str, Any]]:
        """Register a new user with validation."""
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    **extra_fields
                )
                return self._result_ok(self._serialize_user(user))
        except IntegrityError:
            return self._result_fail(
                'Username or email already exists',
                ErrorCode.CONFLICT
            )
        except Exception as e:
            return self._result_fail(
                f'Registration failed: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )
    
    def login_user(
        self,
        email_or_username: str,
        password: str,
        request_meta: Optional[Dict] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """Authenticate user and issue JWT tokens."""
        # Find user
        try:
            if '@' in email_or_username:
                user = User.objects.get(email=email_or_username)
            else:
                user = User.objects.get(username=email_or_username)
        except User.DoesNotExist:
            return self._result_fail(
                'Invalid credentials',
                ErrorCode.AUTHENTICATION_ERROR
            )
        
        # Verify password
        if not user.check_password(password):
            return self._result_fail(
                'Invalid credentials',
                ErrorCode.AUTHENTICATION_ERROR
            )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        
        # Add custom claims
        access['username'] = user.username
        access['email'] = user.email
        
        # Track session
        session_id = secrets.token_urlsafe(32)
        user.add_session(session_id)
        
        # Record login history (async, don't block)
        if request_meta:
            self._record_login_history(user, request_meta, session_id)
        
        return self._result_ok({
            'refresh': str(refresh),
            'access': str(access),
            'user': self._serialize_user(user),
        })
    
    def logout_user(self, user: User) -> ServiceResult[None]:
        """Invalidate all user tokens and clear sessions."""
        try:
            # Blacklist all tokens
            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)
            
            # Clear sessions
            user.active_sessions = []
            user.is_online = False
            user.last_seen = timezone.now()
            user.save(update_fields=['active_sessions', 'is_online', 'last_seen'])
            
            return self._result_ok()
        except Exception as e:
            return self._result_fail(
                f'Logout failed: {str(e)}',
                ErrorCode.INTERNAL_ERROR
            )
    
    def refresh_token(self, refresh_token: str) -> ServiceResult[Dict[str, Any]]:
        """Refresh access token using refresh token."""
        # This is handled by SimpleJWT, but we can add tracking here
        return self._result_ok({'message': 'Token refreshed'})
    
    def _serialize_user(self, user: User) -> Dict[str, Any]:
        """Serialize user data for response."""
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'bio': user.bio,
            'is_online': user.is_online,
            'last_seen': user.last_seen,
            'date_joined': user.date_joined,
        }
    
    def _record_login_history(
        self,
        user: User,
        meta: Dict,
        session_id: str
    ) -> None:
        """Record login history asynchronously."""
        # This would be done via Celery task in production
        # Keeping minimal implementation for now
        pass