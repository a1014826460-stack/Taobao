from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CrawlCreate(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    credential_profile_id: int | None = None
    proxy_profile_id: int | None = None


class JobResponse(BaseModel):
    id: int
    crawler: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    error_code: str | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobResultResponse(BaseModel):
    id: int
    status: str
    result: dict[str, Any]
