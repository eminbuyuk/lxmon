"""
Enhanced error handling and custom exceptions for lxmon-server.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel


class LxmonException(HTTPException):
    """Base exception for lxmon-specific errors."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or f"ERROR_{status_code}"


class ValidationError(LxmonException):
    """Validation error for input data."""

    def __init__(self, detail: str, field: Optional[str] = None):
        error_detail = f"Validation error{f' for field {field}' if field else ''}: {detail}"
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail,
            error_code="VALIDATION_ERROR"
        )


class AuthenticationError(LxmonException):
    """Authentication error."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTHENTICATION_ERROR",
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(LxmonException):
    """Authorization error."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTHORIZATION_ERROR"
        )


class NotFoundError(LxmonException):
    """Resource not found error."""

    def __init__(self, resource: str, resource_id: Any = None):
        detail = f"{resource} not found"
        if resource_id:
            detail += f" with id {resource_id}"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND_ERROR"
        )


class ConflictError(LxmonException):
    """Resource conflict error."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT_ERROR"
        )


class RateLimitError(LxmonException):
    """Rate limit exceeded error."""

    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_ERROR",
            headers={"Retry-After": "60"}
        )


class ServerConnectionError(LxmonException):
    """Server connection error."""

    def __init__(self, server_id: int, detail: str = "Server is not responding"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Server {server_id}: {detail}",
            error_code="SERVER_CONNECTION_ERROR"
        )


class CommandExecutionError(LxmonException):
    """Command execution error."""

    def __init__(self, command: str, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command execution failed: {command} - {detail}",
            error_code="COMMAND_EXECUTION_ERROR"
        )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str


def create_error_response(exception: LxmonException) -> ErrorResponse:
    """Create standardized error response."""
    import datetime
    return ErrorResponse(
        error_code=exception.error_code,
        message=exception.detail,
        timestamp=datetime.datetime.utcnow().isoformat()
    )
