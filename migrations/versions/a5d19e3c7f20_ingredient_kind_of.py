"""ingredients.parent_id: "a kind of" (0.39.0)

Fusilli is a kind of Pasta. A recipe line linked to the general one (Pasta)
is satisfied by any of its kinds in stock; a line linked to a specific kind
still needs that kind. One level only, enforced by the routes: an ingredient
with kinds can't itself be a kind. Additive and nullable.

Revision ID: a5d19e3c7f20
Revises: f2c7d84a1e36
Create Date: 2026-11-15

"""
from alembic import op
import sqlalchemy as sa


revision = 'a5d19e3c7f20'
down_revision = 'f2c7d84a1e36'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_ingredients_parent_id_ingredients',
                                    'ingredients', ['parent_id'], ['id'])


def downgrade():
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ingredients_parent_id_ingredients', type_='foreignkey')
        batch_op.drop_column('parent_id')
