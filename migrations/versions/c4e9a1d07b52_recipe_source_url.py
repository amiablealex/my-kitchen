"""recipes.source_url: where an imported recipe came from (0.34.0)

Revision ID: c4e9a1d07b52
Revises: b8d2e41f7a35
Create Date: 2026-11-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'c4e9a1d07b52'
down_revision = 'b8d2e41f7a35'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_url', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_column('source_url')
