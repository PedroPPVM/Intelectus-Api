"""add_magazine_publication_date_to_process

Revision ID: f1a2b3c4d5e6
Revises: de0ac702bee8
Create Date: 2025-11-19 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'de0ac702bee8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - adicionar magazine_publication_date ao processo."""
    # Adicionar coluna magazine_publication_date para armazenar a data de publicação da revista
    op.add_column('process', sa.Column('magazine_publication_date', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - remover magazine_publication_date do processo."""
    # Remover coluna
    op.drop_column('process', 'magazine_publication_date')

