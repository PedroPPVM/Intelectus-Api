"""Add optimized indexes for company-oriented processes

Revision ID: c8885d61a1f1
Revises: 338f06ee323a
Create Date: 2025-07-20 11:14:42.803848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8885d61a1f1'
down_revision: Union[str, Sequence[str], None] = '338f06ee323a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adicionar índices otimizados para performance de processes orientados por company.
    
    Melhoria do Roadmap Fase 3.1.2 - Processes Orientados a Company:
    - Índice composto (company_id, created_at) - para listagem por empresa ordenada por data
    - Índice composto (company_id, process_type) - para filtros por tipo dentro da empresa  
    - Índice composto (company_id, process_number) - busca rápida por número dentro da empresa
    - Índice composto (company_id, status) - para filtros por status dentro da empresa
    - Índice composto (company_id, updated_at) - para listagem ordenada por atualização
    """
    
    # Verificar se a tabela process existe antes de criar índices
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'process'
        );
    """))
    
    table_exists = result.scalar()
    
    if not table_exists:
        # Se a tabela não existe, pular a criação dos índices
        # (será criada em outra migration)
        return
    
    # Índice para listagem por empresa ordenada por data de criação (use case mais comum)
    # Verificar se o índice já existe antes de criar
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'process' 
            AND indexname = 'ix_process_company_created'
        );
    """))
    
    if not result.scalar():
        op.create_index(
            'ix_process_company_created',
            'process',
            ['company_id', 'created_at'],
            postgresql_using='btree'
        )
    
    # Índice para filtros por tipo dentro da empresa
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'process' 
            AND indexname = 'ix_process_company_type'
        );
    """))
    
    if not result.scalar():
        op.create_index(
            'ix_process_company_type',
            'process', 
            ['company_id', 'process_type'],
            postgresql_using='btree'
        )
    
    # Índice para busca rápida por número do processo dentro da empresa
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'process' 
            AND indexname = 'ix_process_company_number'
        );
    """))
    
    if not result.scalar():
        op.create_index(
            'ix_process_company_number',
            'process',
            ['company_id', 'process_number'], 
            postgresql_using='btree',
            unique=True  # Um processo número por empresa é único
        )
    
    # Índice para filtros por status dentro da empresa
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'process' 
            AND indexname = 'ix_process_company_status'
        );
    """))
    
    if not result.scalar():
        op.create_index(
            'ix_process_company_status',
            'process',
            ['company_id', 'status'],
            postgresql_using='btree'
        )
    
    # Índice para listagem por empresa ordenada por última atualização
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'process' 
            AND indexname = 'ix_process_company_updated'
        );
    """))
    
    if not result.scalar():
        op.create_index(
            'ix_process_company_updated',
            'process',
            ['company_id', 'updated_at'],
            postgresql_using='btree'
        )
    
    # Índice para busca por título dentro da empresa (para searches)
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'process' 
            AND indexname = 'ix_process_company_title_search'
        );
    """))
    
    if not result.scalar():
        op.create_index(
            'ix_process_company_title_search',
            'process',
            ['company_id', 'title'],
            postgresql_using='btree'
        )


def downgrade() -> None:
    """
    Remover índices otimizados para processes orientados por company.
    """
    # Remover todos os índices criados
    op.drop_index('ix_process_company_title_search', table_name='process')
    op.drop_index('ix_process_company_updated', table_name='process')
    op.drop_index('ix_process_company_status', table_name='process')
    op.drop_index('ix_process_company_number', table_name='process')
    op.drop_index('ix_process_company_type', table_name='process')
    op.drop_index('ix_process_company_created', table_name='process')
