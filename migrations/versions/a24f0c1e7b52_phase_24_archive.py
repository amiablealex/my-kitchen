"""archive: recipes.archived_at/archived_by_user_id, generations.archived_at (Phase 24)

Revision ID: a24f0c1e7b52
Revises: 8c61775ddab0
Create Date: 2026-11-09 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a24f0c1e7b52'
down_revision = '8c61775ddab0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('archived_by_user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_recipes_archived_by_user_id_users',
                                    'users', ['archived_by_user_id'], ['id'])

    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.drop_column('archived_at')

    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_constraint('fk_recipes_archived_by_user_id_users', type_='foreignkey')
        batch_op.drop_column('archived_by_user_id')
        batch_op.drop_column('archived_at')
