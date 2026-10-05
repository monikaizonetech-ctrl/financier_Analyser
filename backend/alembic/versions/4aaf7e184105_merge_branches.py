"""merge_branches

Revision ID: 4aaf7e184105
Revises: 2896ec182d2b, 673037a6ba1a
Create Date: 2026-10-05 17:48:23.535657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4aaf7e184105'
down_revision: Union[str, None] = ('2896ec182d2b', '673037a6ba1a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
