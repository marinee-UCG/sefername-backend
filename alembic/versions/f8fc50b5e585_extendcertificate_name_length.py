"""extend certificate name length

Revision ID: f8fc50b5e585
Revises: b3b3f4796e5c
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8fc50b5e585"
down_revision: Union[str, Sequence[str], None] = "b3b3f4796e5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "certificates",
        "cert_name",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=150),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "certificates",
        "cert_name",
        existing_type=sa.String(length=150),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )