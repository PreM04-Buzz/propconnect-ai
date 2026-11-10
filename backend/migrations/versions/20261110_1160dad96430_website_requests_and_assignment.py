"""website requests and assignment

Revision ID: 1160dad96430
Revises: dd589c8c25d1
Create Date: 2026-11-10 20:33:00.715143
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1160dad96430'
down_revision: Union[str, None] = 'dd589c8c25d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clients and leads may now wait unassigned (website requests); the form records consent.
    with op.batch_alter_table("clients") as b:
        b.add_column(sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True))
        b.alter_column("agent_id", existing_type=sa.INTEGER(), nullable=True)
    with op.batch_alter_table("leads") as b:
        b.alter_column("agent_id", existing_type=sa.INTEGER(), nullable=True)
    with op.batch_alter_table("lead_stage_history") as b:
        b.alter_column("changed_by_id", existing_type=sa.INTEGER(), nullable=True)


def downgrade() -> None:
    # Going back requires every client and lead to have an agent: assign or delete
    # unassigned website requests first, or this fails on the NOT NULL constraint.
    with op.batch_alter_table("lead_stage_history") as b:
        b.alter_column("changed_by_id", existing_type=sa.INTEGER(), nullable=False)
    with op.batch_alter_table("leads") as b:
        b.alter_column("agent_id", existing_type=sa.INTEGER(), nullable=False)
    with op.batch_alter_table("clients") as b:
        b.alter_column("agent_id", existing_type=sa.INTEGER(), nullable=False)
        b.drop_column("consent_at")
