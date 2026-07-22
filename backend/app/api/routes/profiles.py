from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.core.config import get_settings
from backend.app.core.crypto import encrypt_secret
from backend.app.db.session import get_db
from backend.app.models.profile import CredentialProfile, ProxyProfile
from backend.app.models.user import User
from backend.app.schemas.profiles import (
    CredentialProfileCreate,
    CredentialProfileResponse,
    ProxyProfileCreate,
    ProxyProfileResponse,
)


router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


def encrypted(value: str | None) -> str | None:
    return encrypt_secret(value, get_settings().credential_encryption_key) if value else None


@router.post("/credentials", response_model=CredentialProfileResponse, status_code=status.HTTP_201_CREATED)
def create_credential_profile(
    payload: CredentialProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> CredentialProfile:
    profile = CredentialProfile(
        user_id=user.id,
        name=payload.name,
        platform=payload.platform,
        purpose=payload.purpose,
        cookie_ciphertext=encrypted(payload.cookie),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/credentials", response_model=list[CredentialProfileResponse])
def list_credential_profiles(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[CredentialProfile]:
    return list(db.scalars(select(CredentialProfile).where(CredentialProfile.user_id == user.id)))


@router.get("/credentials/{profile_id}", response_model=CredentialProfileResponse)
def get_credential_profile(profile_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> CredentialProfile:
    profile = db.get(CredentialProfile, profile_id)
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=404, detail="PROFILE_NOT_FOUND")
    return profile


@router.post("/proxies", response_model=ProxyProfileResponse, status_code=status.HTTP_201_CREATED)
def create_proxy_profile(payload: ProxyProfileCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ProxyProfile:
    profile = ProxyProfile(
        user_id=user.id,
        name=payload.name,
        protocol=payload.protocol,
        host=payload.host,
        port=payload.port,
        username_ciphertext=encrypted(payload.username),
        password_ciphertext=encrypted(payload.password),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/proxies", response_model=list[ProxyProfileResponse])
def list_proxy_profiles(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[ProxyProfile]:
    return list(db.scalars(select(ProxyProfile).where(ProxyProfile.user_id == user.id)))
