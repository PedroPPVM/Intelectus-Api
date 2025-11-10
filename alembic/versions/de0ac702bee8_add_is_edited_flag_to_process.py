"""add_is_edited_flag_to_process

Revision ID: de0ac702bee8
Revises: b2c3d4e5f6a7
Create Date: 2025-11-10 18:13:39.460986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'de0ac702bee8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - adicionar flag is_edited ao processo."""
    # Adicionar coluna is_edited com valor padrão False
    op.add_column('process', sa.Column('is_edited', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    # Criar índice para melhor performance em consultas
    op.create_index(op.f('ix_process_is_edited'), 'process', ['is_edited'], unique=False)


def downgrade() -> None:
    """Downgrade schema - remover flag is_edited do processo."""
    # Remover índice
    op.drop_index(op.f('ix_process_is_edited'), table_name='process')
    # Remover coluna
    op.drop_column('process', 'is_edited')
