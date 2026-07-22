from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.db.base import Base
from backend.app.db.session import build_engine
from backend.app.models import ApiToken, CrawlJob, CredentialProfile, ProxyProfile, User  # noqa: F401


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Compose uses PostgreSQL; creating metadata keeps the local/dev API usable
        # before the first Alembic migration is applied.
        Base.metadata.create_all(build_engine())
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

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(crawls_router)
    app.include_router(jobs_router)
    app.include_router(profiles_router)

    @app.get("/api/v1/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "crawler-api"}

    return app


app = create_app()
