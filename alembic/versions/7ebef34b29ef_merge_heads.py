"""merge heads

Revision ID: 7ebef34b29ef
Revises: 0200b0666e60, enum_fix_001
Create Date: 2025-07-23 00:10:27.969233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ebef34b29ef'
down_revision: Union[str, Sequence[str], None] = ('0200b0666e60', 'enum_fix_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
