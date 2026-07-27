from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.models import ApiToken, CrawlJob, CredentialProfile, ProxyProfile, User  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_online():
    engine = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
