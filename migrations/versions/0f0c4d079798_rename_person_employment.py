"""rename person employment

Revision ID: 0f0c4d079798
Revises: c9fff21c75b2
Create Date: 2026-10-17 18:03:45.655437

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0f0c4d079798"
down_revision = "c9fff21c75b2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_people_employment_type"))

    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.alter_column(
            "employment_type",
            new_column_name="employment",
            existing_type=sa.String(),
            existing_nullable=False,
        )

    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_people_employment"), ["employment"], unique=False)

    op.execute("UPDATE people SET employment = 'employee' WHERE employment = 'permanent'")


def downgrade():
    op.execute("UPDATE people SET employment = 'permanent' WHERE employment = 'employee'")

    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_people_employment"))

    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.alter_column(
            "employment",
            new_column_name="employment_type",
            existing_type=sa.String(),
            existing_nullable=False,
        )

    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_people_employment_type"), ["employment_type"], unique=False)
