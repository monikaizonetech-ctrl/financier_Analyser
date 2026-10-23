"""add missing columns to report_files

Revision ID: bf2f902ff37d
Revises: 4aaf7e184105
Create Date: 2026-10-23 16:32:23.768158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'bf2f902ff37d'
down_revision: Union[str, None] = '4aaf7e184105'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    existing_tables = insp.get_table_names()

    if 'report_files' in existing_tables:
        existing_cols = {c['name'] for c in insp.get_columns('report_files')}

        if 'bank_name' not in existing_cols:
            op.add_column('report_files', sa.Column('bank_name', sa.String(length=100), nullable=True))
        if 'account_holder' not in existing_cols:
            op.add_column('report_files', sa.Column('account_holder', sa.String(length=255), nullable=True))
        if 'masked_account_no' not in existing_cols:
            op.add_column('report_files', sa.Column('masked_account_no', sa.String(length=50), nullable=True))
        if 'owner_restricted' not in existing_cols:
            op.add_column('report_files', sa.Column('owner_restricted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        if 'authenticity_reasons' not in existing_cols:
            op.add_column('report_files', sa.Column('authenticity_reasons', sa.JSON(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    existing_tables = insp.get_table_names()

    if 'report_files' in existing_tables:
        existing_cols = {c['name'] for c in insp.get_columns('report_files')}

        if 'authenticity_reasons' in existing_cols:
            op.drop_column('report_files', 'authenticity_reasons')
        if 'owner_restricted' in existing_cols:
            op.drop_column('report_files', 'owner_restricted')
        if 'masked_account_no' in existing_cols:
            op.drop_column('report_files', 'masked_account_no')
        if 'account_holder' in existing_cols:
            op.drop_column('report_files', 'account_holder')
        if 'bank_name' in existing_cols:
            op.drop_column('report_files', 'bank_name')
