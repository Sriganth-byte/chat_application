"""
Centralized API response formatter.
Provides consistent response structure across all endpoints.
"""
from typing import Optional, Any, Dict
from rest_framework.response import Response
from rest_framework import status


class APIResponse:
    """Standard API response formatter."""
    
    @staticmethod
    def success(
        data: Optional[Any] = None,
        message: str = 'Success',
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """Return success response."""
        return Response({
            'success': True,
            'data': data,
            'message': message,
            'error': None,
        }, status=status_code)
    
    @staticmethod
    def error(
        message: str,
        error_code: str = 'ERROR',
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict] = None
    ) -> Response:
        """Return error response."""
        return Response({
            'success': False,
            'data': None,
            'message': message,
            'error': {
                'code': error_code,
                'details': details,
            }
        }, status=status_code)
    
    @staticmethod
    def paginated(
        data: Any,
        pagination: Dict[str, Any],
        message: str = 'Success'
    ) -> Response:
        """Return paginated response."""
        return Response({
            'success': True,
            'data': data,
            'pagination': pagination,
            'message': message,
        })
    
    @staticmethod
    def created(data: Optional[Any] = None) -> Response:
        """Return 201 Created response."""
        return APIResponse.success(data, 'Created', status.HTTP_201_CREATED)
    
    @staticmethod
    def no_content() -> Response:
        """Return 204 No Content response."""
        return Response(status=status.HTTP_204_NO_CONTENT)