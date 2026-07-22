from passlib.context import CryptContext
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

import jwt

from backend.app.core.config import get_settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    payload = {"sub": subject, "exp": datetime.now(UTC) + timedelta(minutes=30), "type": "access"}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise ValueError("Invalid access token")
    return str(payload["sub"])


def create_api_token() -> tuple[str, str, str]:
    plaintext = "cap_" + token_urlsafe(32)
    return plaintext, sha256(plaintext.encode("utf-8")).hexdigest(), plaintext[:12]
