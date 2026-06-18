"""add is_active to ingredient

Adds Ingredient.is_active (used to "retire" an ingredient: hidden from the
stock list and the wizard, kept in history, reactivatable from the manage area).

The table already holds rows on existing installs, so we add the column with a
temporary server_default of TRUE to backfill those rows, then drop the default
so the column matches the model (Python-side default=True, no server_default).

Revision ID: 63280aee157f
Revises: d33a6431b247
Create Date: 2026-06-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63280aee157f'
down_revision = 'd33a6431b247'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: add the column WITH a server_default so every existing row is
    # backfilled to TRUE (a NOT NULL column can't be added without one).
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_active', sa.Boolean(), nullable=False,
                      server_default=sa.true())
        )
    # Step 2: drop the DB-level default now the backfill is done, leaving the
    # column identical to a fresh create_all (the app sets is_active in Python).
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.alter_column('is_active', server_default=None)


def downgrade():
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.drop_column('is_active')
