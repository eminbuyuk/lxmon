"""
Rate limiting middleware for API protection.
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.config import settings


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.max_requests = 100  # requests per window
        self.window_seconds = 60  # 1 minute window

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]

        # Check if under limit
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True

        return False

    def get_remaining_requests(self, key: str) -> int:
        """Get remaining requests for the key."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]

        return max(0, self.max_requests - len(self.requests[key]))

    def get_reset_time(self, key: str) -> float:
        """Get time until rate limit resets."""
        if not self.requests[key]:
            return 0

        now = time.time()
        oldest_request = min(self.requests[key])
        reset_time = (oldest_request + self.window_seconds) - now
        return max(0, reset_time)


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI."""

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # Add user identifier if authenticated
        user_id = getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None
        rate_limit_key = f"{client_ip}:{user_id}" if user_id else client_ip

        # Check rate limit
        if not rate_limiter.is_allowed(rate_limit_key):
            remaining = rate_limiter.get_remaining_requests(rate_limit_key)
            reset_time = int(rate_limiter.get_reset_time(rate_limit_key))

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error_code": "RATE_LIMIT_ERROR",
                    "message": "Rate limit exceeded",
                    "details": {
                        "remaining_requests": remaining,
                        "reset_in_seconds": reset_time
                    }
                },
                headers={
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(time.time()) + reset_time),
                    "Retry-After": str(reset_time)
                }
            )

        # Add rate limit headers to successful requests
        response = await call_next(request)

        remaining = rate_limiter.get_remaining_requests(rate_limit_key)
        reset_time = int(rate_limiter.get_reset_time(rate_limit_key))

        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + reset_time)

        return response
