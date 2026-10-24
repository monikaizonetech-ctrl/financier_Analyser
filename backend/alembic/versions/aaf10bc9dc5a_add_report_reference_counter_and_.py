"""add_report_reference_counter_and_composite_unique

Revision ID: aaf10bc9dc5a
Revises: 319d8ed6e153
Create Date: 2026-10-24 12:25:40.689748

"""
from collections import defaultdict
from datetime import datetime
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'aaf10bc9dc5a'
down_revision: Union[str, None] = '319d8ed6e153'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REPORT_TYPE_PREFIXES = {
    "BSA": "BSA",
    "GST": "GST",
    "ITR": "ITR",
}


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)

    # 1. Create table report_reference_counters if it does not exist
    existing_tables = insp.get_table_names()
    if "report_reference_counters" not in existing_tables:
        op.create_table(
            "report_reference_counters",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("report_type", sa.String(length=32), nullable=False),
            sa.Column("last_number", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("owner_id", "report_type", name="uq_report_ref_counter_owner_type"),
        )

    # 2. Drop the global unique constraint on reports.reference_id if it exists
    unique_constraints = [c["name"] for c in insp.get_unique_constraints("reports")]
    if "reports_reference_id_key" in unique_constraints:
        op.drop_constraint("reports_reference_id_key", "reports", type_="unique")

    # 3. Deterministically backfill existing reports and initialize the counters
    reports = conn.execute(
        sa.text("SELECT id, owner_id, report_type, reference_id, created_at FROM reports ORDER BY owner_id, report_type, created_at ASC, id ASC")
    ).fetchall()

    groups = defaultdict(list)
    for r in reports:
        groups[(r[1], str(r[2]))].append(r)

    now = datetime.utcnow()
    for (owner_id, report_type_str), r_list in groups.items():
        prefix = REPORT_TYPE_PREFIXES.get(report_type_str.upper(), report_type_str.upper())
        for idx, r in enumerate(r_list, start=1):
            new_ref_id = f"{prefix}_{idx:03d}"
            conn.execute(
                sa.text("UPDATE reports SET reference_id = :ref_id WHERE id = :report_id"),
                {"ref_id": new_ref_id, "report_id": r[0]},
            )

        existing_counter = conn.execute(
            sa.text("SELECT id FROM report_reference_counters WHERE owner_id = :owner_id AND report_type = :report_type"),
            {"owner_id": owner_id, "report_type": report_type_str},
        ).fetchone()

        if existing_counter:
            conn.execute(
                sa.text("UPDATE report_reference_counters SET last_number = :last_num, updated_at = :now WHERE id = :id"),
                {"last_num": len(r_list), "now": now, "id": existing_counter[0]},
            )
        else:
            conn.execute(
                sa.text(
                    "INSERT INTO report_reference_counters (id, owner_id, report_type, last_number, created_at, updated_at) "
                    "VALUES (:id, :owner_id, :report_type, :last_num, :created_at, :updated_at)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "owner_id": owner_id,
                    "report_type": report_type_str,
                    "last_num": len(r_list),
                    "created_at": now,
                    "updated_at": now,
                },
            )

    # 4. Add composite uniqueness constraint on (owner_id, report_type, reference_id)
    insp = inspect(conn)
    current_uniques = [c["name"] for c in insp.get_unique_constraints("reports")]
    if "uq_reports_owner_type_ref_id" not in current_uniques:
        op.create_unique_constraint(
            "uq_reports_owner_type_ref_id",
            "reports",
            ["owner_id", "report_type", "reference_id"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)

    current_uniques = [c["name"] for c in insp.get_unique_constraints("reports")]
    if "uq_reports_owner_type_ref_id" in current_uniques:
        op.drop_constraint("uq_reports_owner_type_ref_id", "reports", type_="unique")

    existing_tables = insp.get_table_names()
    if "report_reference_counters" in existing_tables:
        op.drop_table("report_reference_counters")

    if "reports_reference_id_key" not in current_uniques:
        op.create_unique_constraint("reports_reference_id_key", "reports", ["reference_id"])
