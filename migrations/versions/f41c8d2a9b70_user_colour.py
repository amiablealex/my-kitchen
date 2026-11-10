"""users: colour, a person's chosen colour from the app palette (0.29.3)

Revision ID: f41c8d2a9b70
Revises: e29a4b7c1d63
Create Date: 2026-11-10 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f41c8d2a9b70'
down_revision = 'e29a4b7c1d63'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('colour', sa.String(length=16), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('colour')
