"""
Core service infrastructure for MindConnect.
Provides base classes and common utilities for all services.
"""
from typing import Generic, TypeVar, Optional, Any
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')


class ServiceError(Exception):
    """Base exception for service layer errors."""
    def __init__(self, message: str, code: str = 'SERVICE_ERROR'):
        self.message = message
        self.code = code
        super().__init__(message)


@dataclass
class ServiceResult(Generic[T]):
    """
    Standardized service result wrapper.
    Provides consistent response format across all services.
    """
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    code: str = 'OK'
    
    @classmethod
    def ok(cls, data: Optional[T] = None) -> 'ServiceResult[T]':
        return cls(success=True, data=data, code='OK')
    
    @classmethod
    def fail(cls, error: str, code: str = 'ERROR') -> 'ServiceResult[T]':
        return cls(success=False, error=error, code=code)
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'code': self.code,
        }


class ServiceBase:
    """Base class for all services with common functionality."""
    
    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id
    
    def _result_ok(self, data: Optional[T] = None) -> ServiceResult[T]:
        return ServiceResult.ok(data)
    
    def _result_fail(self, error: str, code: str = 'ERROR') -> ServiceResult[T]:
        return ServiceResult.fail(error, code)


class ErrorCode(str, Enum):
    """Standard error codes for services."""
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    NOT_FOUND = 'NOT_FOUND'
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR'
    RATE_LIMITED = 'RATE_LIMITED'
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    CONFLICT = 'CONFLICT'