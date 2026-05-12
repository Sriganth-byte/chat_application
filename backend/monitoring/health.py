"""
Monitoring configuration for Prometheus metrics.
"""
import time
from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin


class MetricsMiddleware(MiddlewareMixin):
    """Collect request metrics for Prometheus."""
    
    def process_request(self, request: HttpRequest):
        request._start_time = time.time()
    
    def process_response(self, request: HttpRequest, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            # In production, this would push to Prometheus
            # For now, log the metrics
            import logging
            logger = logging.getLogger('metrics')
            logger.info(
                f"path={request.path} "
                f"method={request.method} "
                f"status={response.status_code} "
                f"duration={duration:.3f}s"
            )
        return response


class HealthCheckAPI:
    """Health check endpoints."""
    
    @staticmethod
    def health_check(request):
        """Basic health check."""
        from django.http import JsonResponse
        from django.db import connection
        from django.core.cache import cache
        
        # Check database
        try:
            connection.cursor().execute("SELECT 1")
            db_healthy = True
        except Exception:
            db_healthy = False
        
        # Check cache
        try:
            cache.set('health_check', 'ok', 10)
            cache_healthy = cache.get('health_check') == 'ok'
        except Exception:
            cache_healthy = False
        
        status = 200 if (db_healthy and cache_healthy) else 503
        
        return JsonResponse({
            'status': 'healthy' if status == 200 else 'unhealthy',
            'checks': {
                'database': 'ok' if db_healthy else 'failed',
                'cache': 'ok' if cache_healthy else 'failed',
            }
        }, status=status)
    
    @staticmethod
    def readiness_check(request):
        """Readiness check for Kubernetes."""
        from django.http import JsonResponse
        return JsonResponse({'ready': True})
    
    @staticmethod
    def liveness_check(request):
        """Liveness check for Kubernetes."""
        from django.http import JsonResponse
        return JsonResponse({'alive': True})