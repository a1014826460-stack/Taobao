from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import require_admin
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import UserResponse


router = APIRouter(prefix="/api/v1/admin", tags=["administration"])


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))
