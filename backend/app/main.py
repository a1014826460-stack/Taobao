from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, build_engine
from backend.app.models import ApiToken, CrawlJob, CredentialProfile, ProxyProfile, User  # noqa: F401
from backend.app.core.config import get_settings
from backend.app.core.security import hash_password
from sqlalchemy import select
from sqlalchemy.orm import Session


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Compose uses PostgreSQL; creating metadata keeps the local/dev API usable
        # before the first Alembic migration is applied.
        Base.metadata.create_all(build_engine())
        settings = get_settings()
        session = SessionLocal()
        try:
            admin = session.scalar(select(User).where(User.email == settings.admin_email.lower()))
            if not admin:
                session.add(User(email=settings.admin_email.lower(), password_hash=hash_password(settings.admin_password), is_admin=True, is_formal=True))
                session.commit()
        finally:
            session.close()
        yield

    app = FastAPI(
        title="Crawler API",
        version="0.1.0",
        description="Authenticated asynchronous APIs for Taobao, Tmall, and JD crawlers.",
        lifespan=lifespan,
    )
    from backend.app.api.routes.auth import router as auth_router
    from backend.app.api.routes.admin import router as admin_router
    from backend.app.api.routes.crawls import router as crawls_router
    from backend.app.api.routes.jobs import router as jobs_router
    from backend.app.api.routes.profiles import router as profiles_router
    from backend.app.api.routes.tokens import router as tokens_router

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(crawls_router)
    app.include_router(jobs_router)
    app.include_router(profiles_router)
    app.include_router(tokens_router)

    @app.get("/api/v1/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "crawler-api"}

    return app


app = create_app()
