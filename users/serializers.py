from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.mail import send_mail
from django.conf import settings
import secrets

from .models import User
from backend.utils.media_url import to_relative_url


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    # Read: returns the best available avatar URL
    avatar_url = serializers.SerializerMethodField()
    # Write: accepts a URL string, saved to avatar_url_field on the model
    avatar_url_write = serializers.URLField(
        write_only=True, required=False, allow_blank=True, source='avatar_url_field'
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'avatar', 'avatar_url', 'avatar_url_write',
            'bio', 'is_online', 'last_seen', 'date_joined', 'email_verified',
            'preferences', 'is_staff', 'is_superuser',
        ]
        read_only_fields = [
            'id', 'is_online', 'last_seen', 'date_joined', 'email_verified',
            'is_staff', 'is_superuser',
        ]

    def get_avatar_url(self, obj):
        # External URL (from upload, e.g. Supabase public URL) takes priority.
        # Normalise any old http://127.0.0.1:8000/media/... to a relative path
        # so it resolves correctly on every LAN device via the Vite /media proxy.
        if obj.avatar_url_field:
            return to_relative_url(obj.avatar_url_field)
        # Fall back to ImageField — return a root-relative URL so the path
        # works on any device on the LAN (the Vite proxy forwards /media/* to Django).
        if obj.avatar and hasattr(obj.avatar, 'url'):
            try:
                name = obj.avatar.name
                if name and name != 'avatars/default.png':
                    return obj.avatar.url  # e.g. /media/avatars/abc.jpg
            except Exception:
                pass
        return None




class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'bio')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'password': "Passwords don't match."
            })
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({
                'email': "Email already registered."
            })
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({
                'username': "Username already taken."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        user.verification_token = secrets.token_urlsafe(32)
        user.save()
        self.send_verification_email(user)
        return user

    def send_verification_email(self, user):
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={user.verification_token}"
        send_mail(
            subject='Verify Your MindConnect Email',
            message=f'Click the link to verify: {verification_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional claims - supports email or username login"""

    def validate(self, attrs):
        """Override to support email login"""
        username = attrs.get('username', '')
        email = attrs.get('email', '')
        password = attrs.get('password', '')

        # Support email as username or separate email field
        if email:
            try:
                user = User.objects.get(email=email)
                attrs['username'] = user.username
            except User.DoesNotExist:
                pass

        if username and '@' in username:
            try:
                user = User.objects.get(email=username)
                attrs['username'] = user.username
            except User.DoesNotExist:
                pass

        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        if user.avatar and hasattr(user.avatar, 'url'):
            token['avatar'] = user.avatar.url
        token['is_online'] = user.is_online
        return token


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request"""
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset"""
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'password': "Passwords don't match."
            })
        return attrs
