"""generations: special_request, input_tokens, output_tokens (Phase 25)

Revision ID: b25e7d3a9c41
Revises: a24f0c1e7b52
Create Date: 2026-11-09 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b25e7d3a9c41'
down_revision = 'a24f0c1e7b52'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('special_request', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('input_tokens', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('output_tokens', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.drop_column('output_tokens')
        batch_op.drop_column('input_tokens')
        batch_op.drop_column('special_request')
