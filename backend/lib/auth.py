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
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

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
    Validates token expiry using standard JWT exp claim.
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
        
        # First, check if it's a JWT token we created (with expiry check)
        # Try to decode as our JWT
        try:
            payload = decode_token(token)
            # If we get here, it's our JWT token
            return type('User', (), {
                'id': payload.get('sub'),
                'email': payload.get('email')
            })()
        except HTTPException:
            # Re-raise our own exceptions
            raise
        except Exception:
            # Not our JWT, try Supabase validation
            pass
        
        # Validate with Supabase (handles their token expiry)
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Unauthorized: Invalid token",
                    "error_type": "invalid_token",
                    "suggestion": "Please log in again."
                }
            )
        return user.user
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        # Check for token expiration in Supabase error
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
