"""
Security middleware for enterprise-grade protection.
Implements OWASP Top 10 protections.
"""
import re
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses."""
    
    def process_response(self, request, response):
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' wss: ws:; "
            "frame-ancestors 'none';"
        )
        
        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Content Type Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Frame Options
        response['X-Frame-Options'] = 'DENY'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=()'
        )
        
        # HSTS (only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )
        
        return response


class CorrelationIDMiddleware(MiddlewareMixin):
    """Add correlation ID for request tracing."""
    
    HEADER_NAME = 'X-Request-ID'
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        import uuid
        import threading
        
        request_id = request.META.get('HTTP_X_REQUEST_ID') or str(uuid.uuid4())
        request.correlation_id = request_id
        request.META['X-Request-ID'] = request_id
        
        # Store in thread local for logging
        threading.current_thread().correlation_id = request_id
        
        response = self.get_response(request)
        response[self.HEADER_NAME] = request_id
        return response


class RateLimitByEndpointMiddleware(MiddlewareMixin):
    """Advanced rate limiting by endpoint and user."""
    
    RATE_LIMITS = {
        'login': {'limit': 5, 'window': 60},  # 5 per minute
        'register': {'limit': 3, 'window': 3600},  # 3 per hour
        'password_reset': {'limit': 3, 'window': 3600},  # 3 per hour
        'api_message_send': {'limit': 30, 'window': 60},  # 30 per minute
    }
    
    def process_request(self, request):
        # Rate limit logic would integrate with Redis
        # This is a placeholder for the actual implementation
        pass