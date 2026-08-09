import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.supabase_client import get_anon_client
from core.middleware import get_current_user, AuthenticatedUser

logger = logging.getLogger(__name__)
router = APIRouter()


class SignUpRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup")
async def signup(request: SignUpRequest):
    """Create a new user via Supabase Auth."""
    auth_client = get_anon_client()
    try:
        result = auth_client.auth.sign_up({
            "email": request.email,
            "password": request.password,
        })
    except Exception as e:
        logger.warning(f"Signup failed for {request.email}: {e}")
        raise HTTPException(status_code=400, detail="Unable to sign up with the provided credentials.")

    if not result.user:
        raise HTTPException(status_code=400, detail="Unable to sign up with the provided credentials.")

    session = result.session
    return {
        "message": "Signup successful.",
        "user_id": result.user.id,
        "email": result.user.email,
        "access_token": session.access_token if session else None,
        "refresh_token": session.refresh_token if session else None,
        "email_confirmation_required": session is None,
    }


@router.post("/login")
async def login(request: LoginRequest):
    """Authenticate a user via Supabase Auth and return a real session token."""
    auth_client = get_anon_client()
    try:
        result = auth_client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })
    except Exception as e:
        logger.info(f"Login failed for {request.email}: {e}")
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not result.session:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "token_type": "bearer",
        "expires_in": result.session.expires_in,
        "user_id": result.user.id,
        "email": result.user.email,
    }


@router.get("/me")
async def get_me(user: AuthenticatedUser = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return user.to_dict()