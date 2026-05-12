"""
Health check endpoint — used by load balancers, uptime monitors, and CI.
GET /api/health/ → 200 if all systems nominal, 503 if degraded.
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection, OperationalError
from django.core.cache import cache
from django.utils import timezone
import time


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        checks = {}
        overall = 'ok'

        # Database check
        t0 = time.monotonic()
        try:
            connection.ensure_connection()
            checks['database'] = {'status': 'ok', 'latency_ms': round((time.monotonic() - t0) * 1000, 1)}
        except OperationalError as e:
            checks['database'] = {'status': 'error', 'detail': str(e)}
            overall = 'degraded'

        # Redis cache check
        t0 = time.monotonic()
        try:
            cache.set('_health_ping', 1, timeout=5)
            val = cache.get('_health_ping')
            if val != 1:
                raise ValueError('Cache read/write mismatch')
            checks['cache'] = {'status': 'ok', 'latency_ms': round((time.monotonic() - t0) * 1000, 1)}
        except Exception as e:
            checks['cache'] = {'status': 'error', 'detail': str(e)}
            overall = 'degraded'

        http_status = 200 if overall == 'ok' else 503
        return Response({
            'status': overall,
            'timestamp': timezone.now().isoformat(),
            'version': '2.0.0',
            'checks': checks,
        }, status=http_status)
