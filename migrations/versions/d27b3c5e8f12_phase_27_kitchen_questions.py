"""recipe_comments: @kitchen questions + answers (Phase 27)

Revision ID: d27b3c5e8f12
Revises: c26a1f8e4d07
Create Date: 2026-11-09 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd27b3c5e8f12'
down_revision = 'c26a1f8e4d07'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipe_comments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('kind', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('answer', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('answer_status', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('answered_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('model', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('input_tokens', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('output_tokens', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('recipe_comments', schema=None) as batch_op:
        for col in ('output_tokens', 'input_tokens', 'model', 'answered_at',
                    'answer_status', 'answer', 'kind'):
            batch_op.drop_column(col)
