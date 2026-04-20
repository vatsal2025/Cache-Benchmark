"""Add is_estimated, n_images_used, measurement to attack_runs

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attack_runs", sa.Column("is_estimated", sa.Boolean, server_default="true", nullable=False))
    op.add_column("attack_runs", sa.Column("n_images_used", sa.Integer, server_default="0", nullable=False))
    op.add_column("attack_runs", sa.Column("measurement", postgresql.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("attack_runs", "measurement")
    op.drop_column("attack_runs", "n_images_used")
    op.drop_column("attack_runs", "is_estimated")
