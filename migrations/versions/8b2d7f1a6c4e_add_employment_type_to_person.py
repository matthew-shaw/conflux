"""add employment type to person

Revision ID: 8b2d7f1a6c4e
Revises: df48d66eeeaf
Create Date: 2026-09-07 14:31:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8b2d7f1a6c4e"
down_revision = "df48d66eeeaf"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.add_column(sa.Column("employment_type", sa.String(), nullable=True))

    op.execute("UPDATE people SET employment_type = 'permanent'")

    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.alter_column("employment_type", existing_type=sa.String(), nullable=False)
        batch_op.create_index(batch_op.f("ix_people_employment_type"), ["employment_type"], unique=False)


def downgrade():
    with op.batch_alter_table("people", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_people_employment_type"))
        batch_op.drop_column("employment_type")
