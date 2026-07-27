from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="EMAIL_ALREADY_REGISTERED")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    identifier = payload.email.lower()
    settings = get_settings()
    email = settings.admin_email.lower() if identifier == settings.admin_username.lower() else identifier
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CREDENTIALS")
    return TokenResponse(access_token=create_access_token(str(user.id)))
