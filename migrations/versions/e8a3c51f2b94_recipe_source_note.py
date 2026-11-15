"""recipes.source_note: where a recipe is from, in the household's words (0.37.0)

Revision ID: e8a3c51f2b94
Revises: d7f3b2a96c18
Create Date: 2026-11-15

"""
from alembic import op
import sqlalchemy as sa


revision = 'e8a3c51f2b94'
down_revision = 'd7f3b2a96c18'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_note', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_column('source_note')
