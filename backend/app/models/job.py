from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crawler: Mapped[str] = mapped_column(String(50), index=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    credential_profile_id: Mapped[int | None] = mapped_column(ForeignKey("credential_profiles.id"))
    proxy_profile_id: Mapped[int | None] = mapped_column(ForeignKey("proxy_profiles.id"))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
