"""ai_calls: receipt reads and list matches as countable, priceable calls (0.33.0)

Revision ID: b8d2e41f7a35
Revises: a73e5c19d2f4
Create Date: 2026-11-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'b8d2e41f7a35'
down_revision = 'a73e5c19d2f4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_calls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('ai_calls')
