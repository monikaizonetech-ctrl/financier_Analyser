"""create initial tables

Revision ID: 673037a6ba1a
Revises: 
Create Date: 2026-09-22 12:58:43.136494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app.models.user import UserRole, UserStatus
from app.models.report import ReportType, ReportStatus, FileStatus, FileAuthenticity
from app.models.billing import PlanType, SubscriptionStatus, TransactionType

# revision identifiers, used by Alembic.
revision: str = '673037a6ba1a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    existing_tables = insp.get_table_names()

    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('phone', sa.String(length=20), nullable=True),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('role', sa.Enum(UserRole), nullable=False),
            sa.Column('status', sa.Enum(UserStatus), nullable=False),
            sa.Column('added_by_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['added_by_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    if 'reports' not in existing_tables:
        op.create_table(
            'reports',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('reference_id', sa.String(length=64), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('report_type', sa.Enum(ReportType), nullable=False),
            sa.Column('status', sa.Enum(ReportStatus), nullable=False),
            sa.Column('owner_id', sa.String(length=36), nullable=False),
            sa.Column('result_summary', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('analysed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('reference_id')
        )

    if 'subscriptions' not in existing_tables:
        op.create_table(
            'subscriptions',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('plan', sa.Enum(PlanType), nullable=False),
            sa.Column('status', sa.Enum(SubscriptionStatus), nullable=False),
            sa.Column('credits_total', sa.Float(), nullable=False),
            sa.Column('credits_used', sa.Float(), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id')
        )

    if 'transactions' not in existing_tables:
        op.create_table(
            'transactions',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('type', sa.Enum(TransactionType), nullable=False),
            sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    if 'report_files' not in existing_tables:
        op.create_table(
            'report_files',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('report_id', sa.String(length=36), nullable=False),
            sa.Column('s_no', sa.Integer(), nullable=False),
            sa.Column('file_name', sa.String(length=255), nullable=False),
            sa.Column('stored_path', sa.String(length=500), nullable=False),
            sa.Column('sub_type', sa.String(length=50), nullable=True),
            sa.Column('year', sa.String(length=20), nullable=True),
            sa.Column('password_protected', sa.Boolean(), nullable=False),
            sa.Column('file_status', sa.Enum(FileStatus), nullable=False),
            sa.Column('authenticity', sa.Enum(FileAuthenticity), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    op.drop_table('report_files')
    op.drop_table('transactions')
    op.drop_table('subscriptions')
    op.drop_table('reports')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
