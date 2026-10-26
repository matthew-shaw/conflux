"""gaps as people

Revision ID: 31597b9f84d6
Revises: 0f0c4d079798
Create Date: 2026-10-21 15:00:34.490907

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "31597b9f84d6"
down_revision = "0f0c4d079798"
branch_labels = None
depends_on = None

people = sa.table(
    "people",
    sa.column("is_gap", sa.Boolean()),
)


def upgrade() -> None:
    """Flag gaps on people, move existing team gaps into people as employees."""
    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_gap", sa.Boolean(), server_default=sa.text("false"), nullable=False))
        batch_op.alter_column("name", existing_type=sa.VARCHAR(), nullable=True)
        batch_op.alter_column("location", existing_type=sa.VARCHAR(), nullable=True)
        batch_op.create_index(batch_op.f("ix_people_is_gap"), ["is_gap"], unique=False)


def downgrade() -> None:
    """Remove all gap people and reset Person table."""

    connection = op.get_bind()
    connection.execute(sa.delete(people).where(people.c.is_gap.is_(True)))

    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_people_is_gap"))
        batch_op.alter_column("location", existing_type=sa.VARCHAR(), nullable=False)
        batch_op.alter_column("name", existing_type=sa.VARCHAR(), nullable=False)
        batch_op.drop_column("is_gap")
