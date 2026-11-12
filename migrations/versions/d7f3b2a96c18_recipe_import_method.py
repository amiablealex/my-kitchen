"""recipes.import_method: link | text | photo (0.35.0)

Revision ID: d7f3b2a96c18
Revises: c4e9a1d07b52
Create Date: 2026-11-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'd7f3b2a96c18'
down_revision = 'c4e9a1d07b52'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('import_method', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_column('import_method')
