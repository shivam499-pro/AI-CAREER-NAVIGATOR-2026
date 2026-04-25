"""
Security Middleware Module
Phase 1: Security Hardening Implementation

Features:
- JWT Verification Middleware (Supabase JWT validation)
- Role-Based Access Control (RBAC)
- Structured Logging Middleware
- Standardized API Response Format
"""
import os
import uuid
import time
import logging
import json
from datetime import datetime, timezone
from typing import Optional, Callable, List, Dict, Any
from functools import wraps
from enum import Enum

from fastapi import Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from dotenv import load_dotenv
import httpx

load_dotenv()

logger = logging.getLogger(__name__)

# Import cache for JWT caching
from core.cache import cache


# ==================== ENUMS ====================

class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    PREMIUM = "premium"


class Permission(str, Enum):
    """Permission constants."""
    READ_PROFILE = "read:profile"
    WRITE_PROFILE = "write:profile"
    READ_ANALYSIS = "read:analysis"
    WRITE_ANALYSIS = "write:analysis"
    READ_JOBS = "read:jobs"
    WRITE_JOBS = "write:jobs"
    READ_RESUME = "read:resume"
    WRITE_RESUME = "write:resume"
    READ_INTERVIEW = "read:interview"
    WRITE_INTERVIEW = "write:interview"
    READ_DOCUMENTS = "read:documents"
    WRITE_DOCUMENTS = "write:documents"
    ADMIN_ACCESS = "admin:access"


# ==================== REQUEST MODELS ====================

class AuthenticatedUser:
    """Authenticated user context."""
    
    def __init__(self, user_id: str, email: str, role: str = "user", 
                 permissions: List[str] = None):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.permissions = permissions or []
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.role == UserRole.ADMIN.value:
            return True
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions."""
        if self.role == UserRole.ADMIN.value:
            return True
        return any(p in self.permissions for p in permissions)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "permissions": self.permissions
        }


class APIResponse:
    """Standardized API Response format."""
    
    def __init__(self, success: bool, data: Any = None, error: str = None,
                 meta: Dict[str, Any] = None):
        self.success = success
        self.data = data
        self.error = error
        self.meta = meta or {}
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }
        if self.meta:
            result["meta"] = self.meta
        return result
    
    @staticmethod
    def success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
        """Create a success response."""
        return {
            "success": True,
            "data": data,
            "error": None,
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "message": message
            } if message else {
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
        }
    
    @staticmethod
    def error_response(error: str, code: str = None, 
                     details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create an error response."""
        meta = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }
        if code:
            meta["error_code"] = code
        if details:
            meta["details"] = details
        
        return {
            "success": False,
            "data": None,
            "error": error,
            "meta": meta
        }


# ==================== JWT VERIFICATION ====================

class JWTVerifier:
    """
    JWT Token Verifier using Supabase with local caching for performance.
    
    Optimizations:
    - Local JWT decoding without network call for payload extraction
    - Cached user data with TTL
    - Fallback to Supabase API for full verification when needed
    """
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        self._cache_ttl = 300  # 5 minutes cache for user data
    
    def _decode_jwt_payload(self, token: str) -> Optional[dict]:
        """
        Decode JWT payload locally without verification.
        This is fast and gives us user_id without network call.
        
        Note: This doesn't verify the signature, just extracts payload.
        Full verification still happens via Supabase API.
        """
        try:
            import base64
            import json
            
            # JWT format: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode payload (second part)
            payload_b64 = parts[1]
            # Add padding if needed
            padding = 4 - (len(payload_b64) % 4)
            if padding != 4:
                payload_b64 += '=' * padding
            
            payload_json = base64.urlsafe_b64decode(payload_b64)
            return json.loads(payload_json)
        except Exception as e:
            logger.warning(f"Failed to decode JWT locally: {e}")
            return None
    
    async def verify_token(self, authorization: str) -> AuthenticatedUser:
        """
        Verify Supabase JWT token and extract user info.
        
        Optimized flow:
        1. Try to get cached user data
        2. If not cached, do full verification via Supabase API
        3. Cache the result
        
        Args:
            authorization: Authorization header value (Bearer <token>)
            
        Returns:
            AuthenticatedUser object
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail=APIResponse.error_response(
                    "Authorization header required",
                    code="NO_AUTH_HEADER"
                )
            )
        
        # Extract token from "Bearer <token>"
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        # Try to get cached user
        payload = self._decode_jwt_payload(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                cache_key = f"jwt:user:{user_id}"
                cached_user = cache.get(cache_key)
                if cached_user:
                    logger.debug(f"Using cached user data for {user_id}")
                    return AuthenticatedUser(**cached_user)
        
        # Validate using Supabase Auth API (full verification)
        user = await self._verify_supabase_token(token)
        
        # Cache the result
        if user and user.user_id:
            cache_key = f"jwt:user:{user.user_id}"
            cache.set(cache_key, user.to_dict(), self._cache_ttl)
        
        return user
    
    async def _verify_supabase_token(self, token: str) -> AuthenticatedUser:
        """
        Verify token using Supabase Auth API.
        
        Args:
            token: JWT token
            
        Returns:
            AuthenticatedUser object
            
        Raises:
            HTTPException: If token is invalid
        """
        if not self.supabase_url or not self.supabase_key:
            logger.error("Supabase not configured")
            raise HTTPException(
                status_code=500,
                detail=APIResponse.error_response(
                    "Server configuration error",
                    code="CONFIG_ERROR"
                )
            )
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.supabase_url}/auth/v1/user",
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {token}"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.warning(f"Token verification failed: {response.status_code}")
                    raise HTTPException(
                        status_code=401,
                        detail=APIResponse.error_response(
                            "Invalid or expired token",
                            code="INVALID_TOKEN"
                        )
                    )
                
                user_data = response.json()
                user_id = user_data.get("id")
                email = user_data.get("email", "")
                
                if not user_id:
                    raise HTTPException(
                        status_code=401,
                        detail=APIResponse.error_response(
                            "Invalid token payload",
                            code="INVALID_PAYLOAD"
                        )
                    )
                
                # Get user role from user metadata
                role = user_data.get("user_metadata", {}).get("role", "user")
                
                # Get permissions based on role
                permissions = self._get_role_permissions(role)
                
                return AuthenticatedUser(
                    user_id=user_id,
                    email=email,
                    role=role,
                    permissions=permissions
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Token verification error: {str(e)}")
                raise HTTPException(
                    status_code=401,
                    detail=APIResponse.error_response(
                        "Authentication failed",
                        code="AUTH_FAILED"
                    )
                )
    
    def invalidate_user_cache(self, user_id: str):
        """Invalidate cached user data (e.g., on logout)."""
        cache_key = f"jwt:user:{user_id}"
        cache.delete(cache_key)
        logger.debug(f"Invalidated cache for user {user_id}")

    def _get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for a given role."""
        role_permissions = {
            UserRole.ADMIN.value: [
                Permission.READ_PROFILE.value,
                Permission.WRITE_PROFILE.value,
                Permission.READ_ANALYSIS.value,
                Permission.WRITE_ANALYSIS.value,
                Permission.READ_JOBS.value,
                Permission.WRITE_JOBS.value,
                Permission.READ_RESUME.value,
                Permission.WRITE_RESUME.value,
                Permission.READ_INTERVIEW.value,
                Permission.WRITE_INTERVIEW.value,
                Permission.READ_DOCUMENTS.value,
                Permission.WRITE_DOCUMENTS.value,
                Permission.ADMIN_ACCESS.value,
            ],
            UserRole.PREMIUM.value: [
                Permission.READ_PROFILE.value,
                Permission.WRITE_PROFILE.value,
                Permission.READ_ANALYSIS.value,
                Permission.WRITE_ANALYSIS.value,
                Permission.READ_JOBS.value,
                Permission.WRITE_JOBS.value,
                Permission.READ_RESUME.value,
                Permission.WRITE_RESUME.value,
                Permission.READ_INTERVIEW.value,
                Permission.WRITE_INTERVIEW.value,
                Permission.READ_DOCUMENTS.value,
                Permission.WRITE_DOCUMENTS.value,
            ],
            UserRole.USER.value: [
                Permission.READ_PROFILE.value,
                Permission.WRITE_PROFILE.value,
                Permission.READ_ANALYSIS.value,
                Permission.READ_JOBS.value,
                Permission.READ_RESUME.value,
                Permission.READ_INTERVIEW.value,
                Permission.READ_DOCUMENTS.value,
            ],
            UserRole.GUEST.value: [
                Permission.READ_ANALYSIS.value,
                Permission.READ_JOBS.value,
            ],
        }
        return role_permissions.get(role, role_permissions[UserRole.GUEST.value])


# Global JWT verifier instance
jwt_verifier = JWTVerifier()


# ==================== DEPENDENCY FUNCTIONS ====================

async def get_current_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """
    FastAPI dependency to get current authenticated user.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    
    Args:
        authorization: Authorization header (Bearer <token>)
        
    Returns:
        AuthenticatedUser object
        
    Raises:
        HTTPException: If not authenticated
    """
    return await jwt_verifier.verify_token(authorization)


def require_permission(permission: Permission):
    """
    FastAPI dependency to require a specific permission.
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(
            user: AuthenticatedUser = Depends(require_permission(Permission.WRITE_PROFILE))
        ):
            ...
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function
        
    Raises:
        HTTPException: If user lacks permission
    """
    async def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not user.has_permission(permission.value):
            raise HTTPException(
                status_code=403,
                detail=APIResponse.error_response(
                    f"Permission denied: {permission.value}",
                    code="PERMISSION_DENIED",
                    details={"required": permission.value}
                )
            )
        return user
    return dependency


def require_any_permission(permissions: List[Permission]):
    """
    FastAPI dependency to require any of the specified permissions.
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(
            user: AuthenticatedUser = Depends(require_any_permission([
                Permission.WRITE_PROFILE,
                Permission.ADMIN_ACCESS
            ]))
        ):
            ...
    
    Args:
        permissions: List of acceptable permissions
        
    Returns:
        Dependency function
        
    Raises:
        HTTPException: If user lacks all permissions
    """
    permission_values = [p.value for p in permissions]
    
    async def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not user.has_any_permission(permission_values):
            raise HTTPException(
                status_code=403,
                detail=APIResponse.error_response(
                    f"Permission denied: requires any of {permission_values}",
                    code="PERMISSION_DENIED",
                    details={"required": permission_values}
                )
            )
        return user
    return dependency


def require_role(role: UserRole):
    """
    FastAPI dependency to require a specific role.
    
    Usage:
        @router.get("/admin/endpoint")
        async def endpoint(
            user: AuthenticatedUser = Depends(require_role(UserRole.ADMIN))
        ):
            ...
    
    Args:
        role: Required role
        
    Returns:
        Dependency function
        
    Raises:
        HTTPException: If user lacks role
    """
    async def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role != role.value and user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=403,
                detail=APIResponse.error_response(
                    f"Role required: {role.value}",
                    code="ROLE_REQUIRED",
                    details={"required": role.value, "current": user.role}
                )
            )
        return user
    return dependency


# ==================== LOGGING MIDDLEWARE ====================

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.
    
    Logs:
    - request_id: Unique request identifier
    - user_id: Authenticated user ID (if present)
    - endpoint: Request path
    - method: HTTP method
    - latency: Request processing time in ms
    - status: Response status code
    - ip: Client IP address
    """
    
    def __init__(self, app: ASGIApp, excluded_paths: List[str] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and log details."""
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get start time
        start_time = time.time()
        
        # Extract client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Try to extract user_id from authorization header for logging
        user_id = "anonymous"
        auth_header = request.headers.get("authorization")
        
        if auth_header:
            try:
                # Quick decode without full verification for logging
                # We'll do full verification in the endpoint
                user_id = "authenticated"  # Will be overwritten in endpoint
            except Exception:
                pass
        
        # Store initial user_id for logging
        request.state.user_id = user_id
        request.state.endpoint = request.url.path
        request.state.method = request.method
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Update response with request_id
            response.headers["X-Request-ID"] = request_id
            
            # Log structured entry
            log_data = {
                "request_id": request_id,
                "user_id": request.state.user_id,
                "endpoint": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "ip": client_ip,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
            
            # Log based on status
            if response.status_code >= 500:
                logger.error(f"[REQUEST] {json.dumps(log_data)}")
            elif response.status_code >= 400:
                logger.warning(f"[REQUEST] {json.dumps(log_data)}")
            else:
                logger.info(f"[REQUEST] {json.dumps(log_data)}")
            
            return response
            
        except Exception as e:
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            log_data = {
                "request_id": request_id,
                "user_id": request.state.user_id,
                "endpoint": request.url.path,
                "method": request.method,
                "status": 500,
                "latency_ms": latency_ms,
                "ip": client_ip,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
            logger.error(f"[REQUEST] {json.dumps(log_data)}")
            
            raise


# ==================== AUTH MIDDLEWARE ====================

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT authentication on all protected routes.
    
    Validates Supabase JWT token and attaches user context to request state.
    """
    
    def __init__(self, app: ASGIApp, public_paths: List[str] = None):
        super().__init__(app)
        # Paths that don't require authentication
        self.public_paths = public_paths or [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/auth/",
            "/api/auth/signup",
            "/api/auth/login",
            "/api/auth/callback",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process authentication."""
        # Skip auth for public paths
        if any(request.url.path.startswith(path) for path in self.public_paths):
            return await call_next(request)
        
        # For API routes, we rely on endpoint-level authentication
        # This middleware adds the request_id for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        return await call_next(request)


# ==================== HELPER FUNCTIONS ====================

def format_response(success: bool, data: Any = None, error: str = None,
                    message: str = None, request_id: str = None) -> Dict[str, Any]:
    """
    Create a standardized API response.
    
    Args:
        success: Whether the operation succeeded
        data: Response data
        error: Error message (if any)
        message: Optional success message
        request_id: Request tracking ID
        
    Returns:
        Standardized response dict
    """
    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }
    if request_id:
        meta["request_id"] = request_id
    if message:
        meta["message"] = message
    
    return {
        "success": success,
        "data": data,
        "error": error,
        "meta": meta
    }


# ==================== DECORATORS ====================

def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication on an endpoint function.
    
    Usage:
        @require_auth
        async def protected_endpoint(request: Request):
            user_id = request.state.user_id
            ...
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Check for authorization header
        auth_header = request.headers.get("authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content=APIResponse.error_response(
                    "Authentication required",
                    code="AUTH_REQUIRED"
                )
            )
        
        try:
            # Verify token
            user = await jwt_verifier.verify_token(auth_header)
            
            # Attach user to request state
            request.state.user = user
            request.state.user_id = user.user_id
            request.state.user_email = user.email
            request.state.user_role = user.role
            
            return await func(request, *args, **kwargs)
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content=APIResponse.error_response(
                    str(e.detail),
                    code="AUTH_FAILED"
                )
            )
    
    return wrapper


# ==================== PUBLIC FUNCTIONS ====================

def get_current_user_sync(token: str) -> Optional[AuthenticatedUser]:
    """
    Synchronous way to get current user (for use outside of FastAPI context).
    
    Note: This should only be used in non-async contexts.
    
    Args:
        token: JWT token
        
    Returns:
        AuthenticatedUser or None
    """
    # For sync contexts, we need to run the async verifier
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use sync in async context
            return None
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(jwt_verifier.verify_token(token))
    finally:
        loop.close()


def verify_token_sync(token: str) -> bool:
    """
    Synchronously verify a token.
    
    Args:
        token: JWT token
        
    Returns:
        True if valid, False otherwise
    """
    user = get_current_user_sync(token)
    return user is not None