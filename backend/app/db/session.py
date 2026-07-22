from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import get_settings


def build_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    return create_engine(url, future=True, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})


SessionLocal = sessionmaker(bind=build_engine(), autocommit=False, autoflush=False)


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
