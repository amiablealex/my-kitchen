"""recipe_ingredients.alt_ingredient_id + repair links to deleted ingredients (0.38.0)

Two things:

1. A second, optional catalogue link per recipe line: the "or" alternative
   ("1 cup cauliflower or broccoli"). Either being in stock satisfies the line.
   Only offered where the line's own wording says "or".

2. A one-off data repair. Before 0.38.0, permanently deleting an ingredient
   left recipe lines pointing at an id that no longer exists (SQLite doesn't
   enforce foreign keys here). Those lines looked "not linked" on the recipe
   page but escaped the unlinked note and filter, and silently kept the recipe
   out of suggestions. This clears such dangling links to NULL so they show up
   properly. It's a correction of broken references, not a reshape of valid
   data — the same kind of deliberate exception as 0.30.0's category reorder.

Revision ID: f2c7d84a1e36
Revises: e8a3c51f2b94
Create Date: 2026-11-15

"""
from alembic import op
import sqlalchemy as sa


revision = 'f2c7d84a1e36'
down_revision = 'e8a3c51f2b94'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipe_ingredients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('alt_ingredient_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_recipe_ingredients_alt_ingredient_id_ingredients',
                                    'ingredients', ['alt_ingredient_id'], ['id'])

    op.execute(
        "UPDATE recipe_ingredients SET ingredient_id = NULL "
        "WHERE ingredient_id IS NOT NULL "
        "AND ingredient_id NOT IN (SELECT id FROM ingredients)"
    )


def downgrade():
    with op.batch_alter_table('recipe_ingredients', schema=None) as batch_op:
        batch_op.drop_constraint('fk_recipe_ingredients_alt_ingredient_id_ingredients',
                                 type_='foreignkey')
        batch_op.drop_column('alt_ingredient_id')
