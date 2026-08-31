"""
Authentication routes — register, login, me.

POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

sys.path.insert(0, str(Path(__file__).parent.parent / "database"))
from db import create_user, get_user_by_email, get_user_by_id, init_db

sys.path.insert(0, str(Path(__file__).parent))
from security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: str


# ---------------------------------------------------------------------------
# Helper used by main.py and tests
# ---------------------------------------------------------------------------

def get_current_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode token and return user dict, or None if invalid."""
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return get_user_by_id(uid)


def get_optional_current_user(token: str = Depends(oauth2_scheme)) -> Optional[Dict[str, Any]]:
    """FastAPI dependency — returns user or None (login is optional)."""
    if not token:
        return None
    return get_current_user_from_token(token)


def get_required_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """FastAPI dependency — raises 401 if not authenticated."""
    user = get_optional_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest):
    init_db()  # Idempotent — ensures tables exist
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    hashed = hash_password(body.password)
    user = create_user(email=body.email, password_hash=hashed)
    if user is None:
        raise HTTPException(status_code=409, detail="Email already registered.")

    token = create_access_token({"sub": str(user["id"])})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token({"sub": str(user["id"])})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: Dict[str, Any] = Depends(get_required_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        created_at=current_user.get("created_at", ""),
    )
