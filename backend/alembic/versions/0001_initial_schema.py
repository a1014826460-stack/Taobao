"""initial crawler API schema

Revision ID: 0001_initial_schema
"""

from alembic import op

from backend.app.db.base import Base
from backend.app.models import ApiToken, CrawlJob, CredentialProfile, ProxyProfile, User  # noqa: F401

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
