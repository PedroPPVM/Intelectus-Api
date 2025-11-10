"""Merge rpi_magazine and status_fix heads

Revision ID: b2c3d4e5f6a7
Revises: ('a1b2c3d4e5f6', '9284c95920a8')
Create Date: 2025-01-20 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', '9284c95920a8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Merge das heads: rpi_magazine e status_fix.
    
    Esta migração apenas mescla os dois branches de migração.
    As migrações são independentes:
    - a1b2c3d4e5f6: Cria tabela rpi_magazine e adiciona magazine_id em process
    - 9284c95920a8: Altera tamanho da coluna status em process (100 -> 1000)
    
    Não há conflitos entre as duas migrações, então esta merge é segura.
    """
    # Esta migração de merge não faz alterações no banco
    # Apenas une os dois branches de migração
    pass


def downgrade() -> None:
    """
    Reverter merge.
    """
    pass

