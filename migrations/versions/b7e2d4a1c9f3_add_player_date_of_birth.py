"""add date_of_birth to player (only where it is missing)

The production `player` table already has date_of_birth (legacy column), so
this revision only adds it on databases created from the model, e.g. the
local development SQLite file.

Revision ID: b7e2d4a1c9f3
Revises: a1f3c9d2e7b4
Create Date: 2026-09-24

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7e2d4a1c9f3'
down_revision = 'a1f3c9d2e7b4'
branch_labels = None
depends_on = None


def _has_column():
    columns = sa.inspect(op.get_bind()).get_columns('player')
    return any(c['name'] == 'date_of_birth' for c in columns)


def upgrade():
    if not _has_column():
        op.add_column('player', sa.Column('date_of_birth', sa.Date(), nullable=True))


def downgrade():
    # Intentionally a no-op: in production the column predates this revision
    pass
