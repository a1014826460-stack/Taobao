from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.core.security import create_api_token
from backend.app.db.session import get_db
from backend.app.models.api_token import ApiToken
from backend.app.models.user import User
from backend.app.schemas.tokens import ApiTokenCreate, ApiTokenCreated, ApiTokenResponse


router = APIRouter(prefix="/api/v1/tokens", tags=["API tokens"])


@router.post("", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
def create_token(payload: ApiTokenCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ApiTokenCreated:
    plaintext, digest, prefix = create_api_token()
    token = ApiToken(user_id=user.id, name=payload.name, token_digest=digest, prefix=prefix)
    db.add(token)
    db.commit()
    db.refresh(token)
    return ApiTokenCreated(id=token.id, name=token.name, prefix=token.prefix, token=plaintext)


@router.get("", response_model=list[ApiTokenResponse])
def list_tokens(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[ApiToken]:
    return list(db.scalars(select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.id.desc())))


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(token_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> None:
    token = db.get(ApiToken, token_id)
    if not token or token.user_id != user.id:
        raise HTTPException(status_code=404, detail="TOKEN_NOT_FOUND")
    token.revoked_at = datetime.now(UTC)
    db.commit()
