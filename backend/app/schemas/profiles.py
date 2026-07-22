from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CredentialProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    platform: Literal["taobao", "tmall", "jd"]
    purpose: str | None = Field(default=None, max_length=200)
    cookie: str = Field(min_length=1)


class CredentialProfileResponse(BaseModel):
    id: int
    name: str
    platform: str
    purpose: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProxyProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    protocol: Literal["http", "https", "socks5"]
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=255)


class ProxyProfileResponse(BaseModel):
    id: int
    name: str
    protocol: str
    host: str
    port: int
    created_at: datetime

    model_config = {"from_attributes": True}
