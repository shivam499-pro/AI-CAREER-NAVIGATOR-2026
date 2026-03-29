from fastapi import HTTPException, Header
from typing import Optional
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user from authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: No token provided")
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "")
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid token")
        return user.user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {str(e)}")
