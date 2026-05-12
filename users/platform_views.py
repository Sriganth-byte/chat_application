"""
WebPush, sessions, verification, feature flags, login history, audit log APIs.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import User, UserLoginHistory, WebPushSubscription, FeatureFlag


# ─── WebPush Subscription ─────────────────────────────────────────────────────
class PushSubscribeView(APIView):
    """POST /api/auth/push/subscribe/ — Save browser push subscription"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sub = request.data.get('subscription', {})
        endpoint = sub.get('endpoint', '')
        keys = sub.get('keys', {})
        p256dh = keys.get('p256dh', '')
        auth = keys.get('auth', '')
        if not endpoint or not p256dh or not auth:
            return Response({'error': 'Invalid subscription data'}, status=400)
        obj, created = WebPushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh': p256dh,
                'auth': auth,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                'is_active': True,
            }
        )
        return Response({'subscribed': True, 'created': created})

    def delete(self, request):
        """DELETE — unsubscribe"""
        endpoint = request.data.get('endpoint', '')
        WebPushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response({'unsubscribed': True})


# ─── Session Management ───────────────────────────────────────────────────────
class SessionListView(APIView):
    """GET /api/auth/sessions/ — list active login sessions"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = UserLoginHistory.objects.filter(
            user=request.user, is_active=True
        ).order_by('-logged_in_at')[:20]
        data = [
            {
                'id': s.id,
                'ip_address': s.ip_address,
                'device_type': s.device_type,
                'browser': s.browser_family,
                'os': s.os_family,
                'city': s.city,
                'country': s.country,
                'logged_in_at': s.logged_in_at,
                'is_suspicious': s.is_suspicious,
                'is_current': s.session_key == request.session.session_key if hasattr(request, 'session') else False,
            }
            for s in sessions
        ]
        return Response(data)


class SessionRevokeView(APIView):
    """DELETE /api/auth/sessions/<id>/ — revoke a session"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        session = get_object_or_404(UserLoginHistory, id=pk, user=request.user)
        session.is_active = False
        session.logged_out_at = timezone.now()
        session.save()
        return Response({'revoked': True})


class SessionRevokeAllView(APIView):
    """DELETE /api/auth/sessions/all/ — revoke all sessions"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        UserLoginHistory.objects.filter(user=request.user, is_active=True).update(
            is_active=False, logged_out_at=timezone.now()
        )
        return Response({'revoked_all': True})


# ─── Feature Flags ────────────────────────────────────────────────────────────
class FeatureFlagsView(APIView):
    """GET /api/auth/features/ — get all active feature flags for user"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        flags = FeatureFlag.objects.filter(is_enabled=True)
        result = {}
        for flag in flags:
            result[flag.name] = flag.is_active_for(request.user)
        return Response(result)


# ─── User Verification (Admin) ────────────────────────────────────────────────
class VerifyUserView(APIView):
    """POST /api/auth/users/<id>/verify/ — admin grants verification badge"""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, id=pk)
        action = request.data.get('action', 'verify')
        user.is_verified = (action == 'verify')
        user.verified_at = timezone.now() if action == 'verify' else None
        user.save(update_fields=['is_verified', 'verified_at'])

        # Audit log
        try:
            from reports.models import AuditLog
            AuditLog.objects.create(
                actor=request.user,
                action='verify_user' if action == 'verify' else 'unverify_user',
                target_user=user,
                details={'username': user.username},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        if action == 'verify':
            from notifications.models import Notification
            Notification.objects.create(
                user=user,
                type='system',
                message='🎉 Your account has been verified! You now have a blue checkmark.',
                data={}
            )

        return Response({'verified': user.is_verified, 'username': user.username})


# ─── Audit Log (Admin) ────────────────────────────────────────────────────────
class AuditLogView(APIView):
    """GET /api/auth/audit-log/ — admin audit trail"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from reports.models import AuditLog
        logs = AuditLog.objects.select_related('actor', 'target_user').order_by('-created_at')[:100]
        data = [
            {
                'id': l.id,
                'actor': l.actor.username if l.actor else 'System',
                'action': l.action,
                'target_user': l.target_user.username if l.target_user else None,
                'details': l.details,
                'ip_address': l.ip_address,
                'created_at': l.created_at,
            }
            for l in logs
        ]
        return Response(data)
