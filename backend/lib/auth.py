"""
Auth helper used by routers/profile.py and routers/profile_enhanced.py.

This is intentionally a SEPARATE auth path from core/middleware.py's
JWTVerifier/get_current_user, not a duplicate to be merged blindly:

- core/middleware.get_current_user verifies exclusively against the
  Supabase Auth API and returns an AuthenticatedUser (".user_id", ".role",
  ".permissions", ...). It has no offline/custom-token path.
- lib.auth.get_current_user (below) tries Supabase first, then falls back
  to decoding a locally-issued JWT (see create_access_token/decode_token)
  signed with JWT_SECRET_KEY, and returns an object shaped as ".id"/".email"
  instead. The test suite relies on this fallback to mint tokens for
  routers/profile*.py without a live Supabase call (see tests/conftest.py's
  mock_user.user = None, and tests/integration/conftest.py).

If these two are ever unified, the migration has to reconcile the
".user_id" vs ".id" attribute mismatch across every profile.py/
profile_enhanced.py call site AND give the middleware verifier an
equivalent offline-token path (or rewrite those tests to hit a mocked
Supabase instead) - not something to do as a drive-by edit.
"""
from fastapi import HTTPException, Header
from typing import Optional
from supabase import create_client
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta, timezone

# Load environment variables
load_dotenv()

# JWT Configuration
#
# There is no hardcoded fallback here on purpose: a fallback secret is a
# secret an attacker can read from source control. If JWT_SECRET_KEY is
# missing, left at the placeholder from .env.example, or too short, refuse
# to start rather than silently signing/accepting tokens with a guessable
# key - this key is also what verifies the custom-JWT fallback branch in
# get_current_user() below, so a weak value here is directly exploitable
# as a token-forgery vector.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"

_INSECURE_JWT_SECRETS = {
    "your-super-secret-key-change-in-production",
    "your-jwt-secret-key-min-32-chars-change-in-production",
}
if not JWT_SECRET_KEY or JWT_SECRET_KEY in _INSECURE_JWT_SECRETS or len(JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY must be set to a random secret of at least 32 "
        "characters (see .env.example) before the app can start. Refusing "
        "to start with a missing, placeholder, or too-short JWT signing key."
    )

# Token expiry times
ACCESS_TOKEN_EXPIRE_HOURS = 1  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)


def create_access_token(user_id: str, email: str) -> str:
    """
    Create a JWT access token with expiry.
    Token expires after ACCESS_TOKEN_EXPIRE_HOURS (default: 1 hour).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, email: str) -> str:
    """
    Create a JWT refresh token with expiry.
    Token expires after REFRESH_TOKEN_EXPIRE_DAYS (default: 7 days).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": "refresh",
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Returns the payload if valid, raises exception if expired or invalid.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp:
            now = int(datetime.now(timezone.utc).timestamp())
            if exp < now:
                raise jwt.ExpiredSignatureError("Token has expired")
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Token has expired. Please re-authenticate.",
                "error_type": "token_expired",
                "suggestion": "Please log in again to get a new token."
            }
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Invalid token. Please re-authenticate.",
                "error_type": "invalid_token",
                "suggestion": "Please log in again."
            }
        )


def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Get current user from authorization header.
    Validates token using Supabase first, then falls back to custom JWT.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Unauthorized: No token provided",
                "error_type": "no_token",
                "suggestion": "Please provide a valid authentication token."
            }
        )
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "")
        
        # First, try Supabase token validation (for Supabase access tokens)
        try:
            user = supabase.auth.get_user(token)
            if user and user.user:
                return user.user
        except Exception as supabase_error:
            # Supabase validation failed, try custom JWT as fallback
            pass
        
        # Fallback: Try to decode as custom JWT token
        try:
            payload = decode_token(token)
            return type('User', (), {
                'id': payload.get('sub'),
                'email': payload.get('email')
            })()
        except HTTPException:
            raise
        except Exception:
            # Neither Supabase nor custom JWT worked
            pass
        
        # Both validation methods failed
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Unauthorized: Invalid token",
                "error_type": "invalid_token",
                "suggestion": "Please log in again."
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        # Check for token expiration in error
        if "expired" in error_str or "token" in error_str:
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Session expired. Please re-authenticate.",
                    "error_type": "token_expired",
                    "suggestion": "Please log in again to get a new session."
                }
            )
        raise HTTPException(
            status_code=401,
            detail={
                "message": f"Unauthorized: {str(e)}",
                "error_type": "authentication_error",
                "suggestion": "Please log in again."
            }
        )