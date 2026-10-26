"""increase_year_and_sub_type_length_in_report_files

Revision ID: bc87bf697e1d
Revises: aaf10bc9dc5a
Create Date: 2026-10-26 14:44:35.509555

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc87bf697e1d'
down_revision: Union[str, None] = 'aaf10bc9dc5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('report_files', 'year',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.VARCHAR(length=100),
               existing_nullable=True)
    op.alter_column('report_files', 'sub_type',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.VARCHAR(length=100),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('report_files', 'sub_type',
               existing_type=sa.VARCHAR(length=100),
               type_=sa.VARCHAR(length=50),
               existing_nullable=True)
    op.alter_column('report_files', 'year',
               existing_type=sa.VARCHAR(length=100),
               type_=sa.VARCHAR(length=20),
               existing_nullable=True)
