"""convert_file_status_and_authenticity_to_varchar

Revision ID: 319d8ed6e153
Revises: bf2f902ff37d
Create Date: 2026-10-23 17:43:03.224673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '319d8ed6e153'
down_revision: Union[str, None] = 'bf2f902ff37d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    existing_tables = insp.get_table_names()

    if 'report_files' in existing_tables:
        if conn.dialect.name == 'postgresql':
            # 1. Convert file_status column to VARCHAR(50)
            conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN file_status DROP DEFAULT"))
            conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN file_status TYPE VARCHAR(50) USING file_status::text"))
            conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN file_status SET DEFAULT 'Uploaded'"))

            # 2. Convert authenticity column to VARCHAR(50)
            conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN authenticity DROP DEFAULT"))
            conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN authenticity TYPE VARCHAR(50) USING authenticity::text"))
            conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN authenticity SET DEFAULT 'Pending'"))
        else:
            op.alter_column('report_files', 'file_status', type_=sa.String(length=50), existing_nullable=False, server_default='Uploaded')
            op.alter_column('report_files', 'authenticity', type_=sa.String(length=50), existing_nullable=False, server_default='Pending')

        # 3. Normalize all existing uppercase ENUM values to Python string values
        # file_status values
        conn.execute(sa.text("UPDATE report_files SET file_status = 'Processed' WHERE file_status = 'PROCESSED'"))
        conn.execute(sa.text("UPDATE report_files SET file_status = 'Uploaded' WHERE file_status = 'UPLOADED'"))
        conn.execute(sa.text("UPDATE report_files SET file_status = 'Processing' WHERE file_status = 'PROCESSING'"))
        conn.execute(sa.text("UPDATE report_files SET file_status = 'Failed' WHERE file_status IN ('FAILED', 'ERROR')"))
        conn.execute(sa.text("UPDATE report_files SET file_status = 'Password required' WHERE file_status = 'PASSWORD_REQUIRED'"))
        conn.execute(sa.text("UPDATE report_files SET file_status = 'Unlocked' WHERE file_status = 'UNLOCKED'"))

        # authenticity values
        conn.execute(sa.text("UPDATE report_files SET authenticity = 'Original' WHERE authenticity IN ('VERIFIED', 'ORIGINAL')"))
        conn.execute(sa.text("UPDATE report_files SET authenticity = 'Pending' WHERE authenticity = 'PENDING'"))
        conn.execute(sa.text("UPDATE report_files SET authenticity = 'Suspicious' WHERE authenticity = 'SUSPICIOUS'"))
        conn.execute(sa.text("UPDATE report_files SET authenticity = 'Tampered' WHERE authenticity = 'TAMPERED'"))
        conn.execute(sa.text("UPDATE report_files SET authenticity = 'Unverifiable' WHERE authenticity = 'UNVERIFIABLE'"))


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if 'report_files' in insp.get_table_names():
        if conn.dialect.name == 'postgresql':
            try:
                conn.execute(sa.text("UPDATE report_files SET file_status = UPPER(file_status)"))
                conn.execute(sa.text("UPDATE report_files SET authenticity = UPPER(authenticity)"))
                conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN file_status TYPE filestatus USING file_status::filestatus"))
                conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN authenticity TYPE fileauthenticity USING authenticity::fileauthenticity"))
            except Exception:
                pass
