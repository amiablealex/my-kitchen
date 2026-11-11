"""categories: display_order becomes a position within the section (0.30.0)

Data only. Renumbers each section's categories 1..n, keeping their current
relative order (display_order, then name), so nothing moves on upgrade except
that sections now stay together.

Revision ID: a73e5c19d2f4
Revises: f41c8d2a9b70
Create Date: 2026-11-11 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a73e5c19d2f4'
down_revision = 'f41c8d2a9b70'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, section FROM categories ORDER BY section, display_order, lower(name)"
    )).fetchall()
    pos = {}
    for cid, section in rows:
        pos[section] = pos.get(section, 0) + 1
        conn.execute(sa.text("UPDATE categories SET display_order = :p WHERE id = :i"),
                     {"p": pos[section], "i": cid})


def downgrade():
    # Nothing to undo: older code sorts by display_order alone, so it just
    # interleaves the sections again.
    pass
