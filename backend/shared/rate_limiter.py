"""
Enhanced Rate Limiting with Per-User and Burst Protection

This module provides advanced rate limiting capabilities beyond basic IP-based limiting.
"""
import logging
from typing import Optional
from fastapi import Request, HTTPException
from shared.redis_client import auth_cache
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Advanced rate limiter with:
    - Per-user rate limiting
    - Burst protection
    - Token bucket algorithm
    """
    
    def __init__(self):
        self.redis = auth_cache
    
    def check_rate_limit(
        self, 
        user_id: Optional[str], 
        ip_address: str,
        endpoint: str,
        max_requests: int = 100,
        window_seconds: int = 60,
        burst_limit: int = 10,
        burst_window: int = 1
    ) -> bool:
        """
        Check if request should be rate limited.
        
        Args:
            user_id: User ID if authenticated
            ip_address: Client IP address
            endpoint: API endpoint being accessed
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            burst_limit: Maximum burst requests
            burst_window: Burst window in seconds
            
        Returns:
            True if request is allowed, raises HTTPException if rate limited
        """
        current_time = int(time.time())
        
        # Check burst limit first (short window)
        burst_key = f"burst:{user_id or ip_address}:{endpoint}"
        burst_count = self.redis.incr_with_expire(burst_key, burst_window)
        
        if burst_count > burst_limit:
            logger.warning(
                f"Burst limit exceeded for {user_id or ip_address} on {endpoint}: "
                f"{burst_count}/{burst_limit} in {burst_window}s"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Please wait {burst_window} second(s).",
                headers={"Retry-After": str(burst_window)}
            )
        
        # Check per-user limit (if authenticated)
        if user_id:
            user_key = f"ratelimit:user:{user_id}:{endpoint}"
            user_count = self.redis.incr_with_expire(user_key, window_seconds)
            
            if user_count > max_requests:
                logger.warning(
                    f"User rate limit exceeded for {user_id} on {endpoint}: "
                    f"{user_count}/{max_requests} in {window_seconds}s"
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.",
                    headers={
                        "Retry-After": str(window_seconds),
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": str(max(0, max_requests - user_count)),
                        "X-RateLimit-Reset": str(current_time + window_seconds)
                    }
                )
        
        # Check per-IP limit (always check as fallback)
        ip_key = f"ratelimit:ip:{ip_address}:{endpoint}"
        ip_count = self.redis.incr_with_expire(ip_key, window_seconds)
        
        # IP limit is typically higher than user limit
        ip_max = max_requests * 2
        if ip_count > ip_max:
            logger.warning(
                f"IP rate limit exceeded for {ip_address} on {endpoint}: "
                f"{ip_count}/{ip_max} in {window_seconds}s"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for your IP address.",
                headers={"Retry-After": str(window_seconds)}
            )
        
        return True
    
    def get_remaining_quota(self, user_id: str, endpoint: str, max_requests: int = 100) -> int:
        """Get remaining requests for user."""
        user_key = f"ratelimit:user:{user_id}:{endpoint}"
        current_count = int(self.redis.get(user_key) or 0)
        return max(0, max_requests - current_count)


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit_for_request(request: Request, max_requests: int = 100, window_seconds: int = 60):
    """
    Dependency function to check rate limits for a request.
    
    Usage:
        @app.post("/api/endpoint")
        def my_endpoint(
            request: Request,
            _rate_limit: bool = Depends(lambda r: check_rate_limit_for_request(r, 50, 60))
        ):
            ...
    """
    user_id = request.headers.get("X-User-ID")
    ip_address = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    
    return rate_limiter.check_rate_limit(
        user_id=user_id,
        ip_address=ip_address,
        endpoint=endpoint,
        max_requests=max_requests,
        window_seconds=window_seconds
    )
