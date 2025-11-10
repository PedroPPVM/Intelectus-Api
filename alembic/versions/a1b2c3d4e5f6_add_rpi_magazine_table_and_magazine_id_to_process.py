"""Add rpi_magazine table and magazine_id to process

Revision ID: a1b2c3d4e5f6
Revises: c8885d61a1f1
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c8885d61a1f1'
branch_labels: Union[str, Sequence[str], None] = ('rpi_magazine',)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Criar tabela rpi_magazine e adicionar campo magazine_id na tabela process.
    
    Sistema de controle de versões de revistas RPI:
    - Tabela rpi_magazine armazena informações sobre revistas baixadas
    - Campo magazine_id em process rastreia qual revista foi usada para atualizar cada processo
    """
    
    # Criar tabela rpi_magazine
    op.create_table(
        'rpi_magazine',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('process_type', postgresql.ENUM('BRAND', 'PATENT', 'DESIGN', 'SOFTWARE', name='processtype', create_type=False), nullable=False),
        sa.Column('magazine_identifier', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Criar índices para rpi_magazine
    op.create_index('ix_rpi_magazine_id', 'rpi_magazine', ['id'], unique=False)
    op.create_index('ix_rpi_magazine_process_type', 'rpi_magazine', ['process_type'], unique=False)
    op.create_index('ix_rpi_magazine_magazine_identifier', 'rpi_magazine', ['magazine_identifier'], unique=False)
    op.create_index('ix_rpi_magazine_type_identifier', 'rpi_magazine', ['process_type', 'magazine_identifier'], unique=False)
    
    # Adicionar coluna magazine_id na tabela process
    op.add_column('process', sa.Column('magazine_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Criar foreign key constraint
    op.create_foreign_key(
        'fk_process_magazine_id',
        'process',
        'rpi_magazine',
        ['magazine_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Criar índice para magazine_id em process
    op.create_index('ix_process_magazine_id', 'process', ['magazine_id'], unique=False)


def downgrade() -> None:
    """
    Remover tabela rpi_magazine e campo magazine_id da tabela process.
    """
    # Remover índice e foreign key
    op.drop_index('ix_process_magazine_id', table_name='process')
    op.drop_constraint('fk_process_magazine_id', 'process', type_='foreignkey')
    
    # Remover coluna magazine_id
    op.drop_column('process', 'magazine_id')
    
    # Remover índices e tabela rpi_magazine
    op.drop_index('ix_rpi_magazine_type_identifier', table_name='rpi_magazine')
    op.drop_index('ix_rpi_magazine_magazine_identifier', table_name='rpi_magazine')
    op.drop_index('ix_rpi_magazine_process_type', table_name='rpi_magazine')
    op.drop_index('ix_rpi_magazine_id', table_name='rpi_magazine')
    op.drop_table('rpi_magazine')

