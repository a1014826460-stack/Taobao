import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./backend_test.db"
os.environ["CREDENTIAL_ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

from backend.app.api.routes.auth import get_db
from backend.app.db.base import Base
from backend.app.main import create_app
from backend.app.models import ApiToken, CrawlJob, CredentialProfile, ProxyProfile, User  # noqa: F401


@pytest.fixture
def client(tmp_path: Path):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    app = create_app()

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)


@pytest.fixture
def auth_headers(client):
    client.post("/api/v1/auth/register", json={"email": "member@example.com", "password": "CorrectHorse1!"})
    token = client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "CorrectHorse1!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
