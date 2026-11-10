"""recipe_comments: suggested_change for @kitchen answers (Phase 29)

Revision ID: e29a4b7c1d63
Revises: d27b3c5e8f12
Create Date: 2026-11-10 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e29a4b7c1d63'
down_revision = 'd27b3c5e8f12'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipe_comments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('suggested_change', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('recipe_comments', schema=None) as batch_op:
        batch_op.drop_column('suggested_change')
