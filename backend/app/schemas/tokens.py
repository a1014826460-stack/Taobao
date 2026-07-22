from datetime import datetime

from pydantic import BaseModel, Field


class ApiTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ApiTokenCreated(BaseModel):
    id: int
    name: str
    prefix: str
    token: str


class ApiTokenResponse(BaseModel):
    id: int
    name: str
    prefix: str
    revoked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
