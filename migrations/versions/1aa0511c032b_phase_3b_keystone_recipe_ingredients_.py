"""Phase 3b keystone: recipe_ingredients + recipes meta (source, meal_type, author, nullable generation_id)

Revision ID: 1aa0511c032b
Revises: f3c9a72b4e10
Create Date: 2026-06-27 15:23:08.395939

"""
from alembic import op
import sqlalchemy as sa


revision = '1aa0511c032b'
down_revision = 'f3c9a72b4e10'
branch_labels = None
depends_on = None


def upgrade():
    # recipe_ingredients: ingredients become a first-class, joinable table. raw_text
    # NOT NULL (the AI's item string, always present); ingredient_id NULLABLE (the
    # resolver link, null when unmatched); amount/unit stored as text (verbatim AI
    # output — non-numeric amounts like "a splash"/"½" are valid).
    op.create_table('recipe_ingredients',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('ingredient_id', sa.Integer(), nullable=True),
    sa.Column('raw_text', sa.String(), nullable=False),
    sa.Column('amount', sa.String(), nullable=True),
    sa.Column('unit', sa.String(), nullable=True),
    sa.Column('to_buy', sa.Boolean(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.id'], ),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        # source NOT NULL: add with a TEMPORARY server_default='ai' so existing
        # rows backfill during the SQLite table rebuild (the reusable
        # add-NOT-NULL-on-a-populated-table pattern). The default is dropped below.
        batch_op.add_column(sa.Column('source', sa.String(), nullable=False, server_default='ai'))
        batch_op.add_column(sa.Column('meal_type', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('created_by_user_id', sa.Integer(), nullable=True))
        # generation_id becomes nullable (user/imported recipes have no generation).
        batch_op.alter_column('generation_id',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.create_foreign_key(
            'fk_recipes_created_by_user_id_users', 'users',
            ['created_by_user_id'], ['id'])

    # Drop the temporary server_default now existing rows are backfilled, so the
    # steady-state column has no DB default and the write path stays authoritative.
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.alter_column('source', existing_type=sa.String(), server_default=None)


def downgrade():
    # Dropping created_by_user_id removes its FK in the SQLite batch rebuild — no
    # separate drop_constraint needed (and none can be dropped by name on SQLite).
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_column('created_by_user_id')
        batch_op.drop_column('meal_type')
        batch_op.drop_column('source')
        batch_op.alter_column('generation_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    op.drop_table('recipe_ingredients')
