"""
2FA / TOTP views using django-otp (already installed).
Provides setup (QR code), verify (token check), and disable.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import pyotp
import qrcode
import qrcode.image.svg
import io
import base64


class TOTPSetupView(APIView):
    """GET /api/auth/2fa/setup/ — generate TOTP secret + QR code"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Generate or retrieve secret
        from django.core.cache import cache
        cache_key = f'totp_secret:{user.id}'

        secret = cache.get(cache_key)
        if not secret:
            secret = pyotp.random_base32()
            cache.set(cache_key, secret, timeout=600)  # 10min to complete setup

        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=user.email,
            issuer_name='MindConnect'
        )

        # Generate QR code as base64 PNG
        img = qrcode.make(uri)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_b64 = base64.b64encode(buffer.getvalue()).decode()

        return Response({
            'secret': secret,
            'qr_code': f'data:image/png;base64,{qr_b64}',
            'manual_entry_key': secret,
        })

    def post(self, request):
        """POST /api/auth/2fa/setup/ — confirm setup with a valid TOTP token"""
        user = request.user
        token = request.data.get('token', '').strip()

        from django.core.cache import cache
        cache_key = f'totp_secret:{user.id}'
        secret = cache.get(cache_key)

        if not secret:
            return Response({'error': 'Setup session expired. Start again.'}, status=400)

        totp = pyotp.TOTP(secret)
        if not totp.verify(token, valid_window=1):
            return Response({'error': 'Invalid code. Try again.'}, status=400)

        # Save to user profile
        profile = user.profile if hasattr(user, 'profile') else None
        try:
            from social.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.totp_secret = secret
            profile.totp_enabled = True
            profile.save(update_fields=['totp_secret', 'totp_enabled'])
        except Exception:
            pass

        cache.delete(cache_key)
        return Response({'message': '2FA enabled successfully!'})


class TOTPVerifyView(APIView):
    """POST /api/auth/2fa/verify/ — verify a TOTP code at login"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token', '').strip()
        user = request.user

        try:
            from social.models import UserProfile
            profile = UserProfile.objects.get(user=user, totp_enabled=True)
            totp = pyotp.TOTP(profile.totp_secret)
            if totp.verify(token, valid_window=1):
                return Response({'verified': True})
            return Response({'verified': False, 'error': 'Invalid code'}, status=400)
        except UserProfile.DoesNotExist:
            return Response({'error': '2FA not enabled'}, status=400)


class TOTPDisableView(APIView):
    """DELETE /api/auth/2fa/disable/ — disable 2FA"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        password = request.data.get('password', '')
        if not request.user.check_password(password):
            return Response({'error': 'Incorrect password'}, status=403)

        try:
            from social.models import UserProfile
            profile = UserProfile.objects.get(user=request.user)
            profile.totp_secret = ''
            profile.totp_enabled = False
            profile.save(update_fields=['totp_secret', 'totp_enabled'])
            return Response({'message': '2FA disabled'})
        except UserProfile.DoesNotExist:
            return Response({'error': '2FA not enabled'}, status=400)
