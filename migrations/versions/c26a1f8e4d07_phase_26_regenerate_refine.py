"""generations: kind, parent_generation_id, source_recipe_id, instruction (Phase 26)

Revision ID: c26a1f8e4d07
Revises: b25e7d3a9c41
Create Date: 2026-11-09 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c26a1f8e4d07'
down_revision = 'b25e7d3a9c41'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('kind', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('parent_generation_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('source_recipe_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('instruction', sa.Text(), nullable=True))
        batch_op.create_foreign_key('fk_generations_parent_generation_id_generations',
                                    'generations', ['parent_generation_id'], ['id'])
        batch_op.create_foreign_key('fk_generations_source_recipe_id_recipes',
                                    'recipes', ['source_recipe_id'], ['id'])


def downgrade():
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.drop_constraint('fk_generations_source_recipe_id_recipes', type_='foreignkey')
        batch_op.drop_constraint('fk_generations_parent_generation_id_generations', type_='foreignkey')
        batch_op.drop_column('instruction')
        batch_op.drop_column('source_recipe_id')
        batch_op.drop_column('parent_generation_id')
        batch_op.drop_column('kind')
