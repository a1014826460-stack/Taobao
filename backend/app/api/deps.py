from hashlib import sha256

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.api_token import ApiToken


bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_REQUIRED")
    token = credentials.credentials
    if token.startswith("cap_"):
        api_token = db.scalar(select(ApiToken).where(ApiToken.token_digest == sha256(token.encode("utf-8")).hexdigest()))
        if not api_token or api_token.revoked_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_TOKEN")
        user_id = api_token.user_id
    else:
        try:
            user_id = int(decode_access_token(token))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_TOKEN") from exc
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_TOKEN")
    return user


def current_api_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> ApiToken | None:
    if not credentials or not credentials.credentials.startswith("cap_"):
        return None
    digest = sha256(credentials.credentials.encode("utf-8")).hexdigest()
    token = db.scalar(select(ApiToken).where(ApiToken.token_digest == digest))
    return token if token and not token.revoked_at else None


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ADMIN_REQUIRED")
    return user
