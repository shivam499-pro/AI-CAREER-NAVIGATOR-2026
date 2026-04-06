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
