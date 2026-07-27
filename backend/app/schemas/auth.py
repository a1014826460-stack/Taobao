from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)


class LoginRequest(BaseModel):
    # Login also accepts the configured administrator username (for example,
    # `admin`) while registration remains email-only.
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=10, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    trial_successes_remaining: int
    is_formal: bool

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    is_formal: bool | None = None
    trial_successes_remaining: int | None = Field(default=None, ge=0)
