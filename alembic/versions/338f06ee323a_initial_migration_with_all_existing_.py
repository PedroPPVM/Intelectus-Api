"""Initial migration with all existing tables

Revision ID: 338f06ee323a
Revises: 
Create Date: 2025-07-20 10:55:39.462986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Nota: Tabelas criadas manualmente baseadas nos modelos SQLAlchemy


# revision identifiers, used by Alembic.
revision: str = '338f06ee323a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - criar todas as tabelas iniciais."""
    
    # Criar tipos ENUM primeiro
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE processtype AS ENUM ('BRAND', 'PATENT', 'DESIGN', 'SOFTWARE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE processsituation AS ENUM ('FILED', 'PUBLISHED', 'UNDER_EXAMINATION', 'OPPOSED', 'GRANTED', 'EXPIRED', 'LAPSED', 'RENEWED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE alerttype AS ENUM ('mudanca_status', 'publicacao', 'prazo', 'processo_similar', 'renovacao_vencimento');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE membershiprole AS ENUM ('member', 'admin', 'owner', 'viewer');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE membershippermission AS ENUM ('read_processes', 'create_processes', 'update_processes', 'delete_processes', 'read_company_data', 'update_company_data', 'manage_users', 'view_reports', 'manage_billing');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Criar tabela user
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_id'), 'user', ['id'], unique=False)
    
    # Criar tabela company
    op.create_table(
        'company',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('document', sa.String(length=20), nullable=False, unique=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=2), nullable=True),
        sa.Column('zip_code', sa.String(length=10), nullable=True),
        sa.Column('country', sa.String(length=50), nullable=True, server_default='Brasil'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_id'), 'company', ['id'], unique=False)
    op.create_index(op.f('ix_company_name'), 'company', ['name'], unique=False)
    
    # Criar tabela user_company_association
    op.create_table(
        'user_company_association',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'company_id')
    )
    
    # Criar tabela process
    op.create_table(
        'process',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_type', postgresql.ENUM('BRAND', 'PATENT', 'DESIGN', 'SOFTWARE', name='processtype', create_type=False), nullable=False),
        sa.Column('process_number', sa.String(length=50), nullable=False, unique=True),
        sa.Column('title', sa.String(length=1000), nullable=False),
        sa.Column('depositor', sa.String(length=500), nullable=True),
        sa.Column('cnpj_depositor', sa.String(length=20), nullable=True),
        sa.Column('cpf_depositor', sa.String(length=15), nullable=True),
        sa.Column('attorney', sa.String(length=500), nullable=True),
        sa.Column('deposit_date', sa.Date(), nullable=True),
        sa.Column('concession_date', sa.Date(), nullable=True),
        sa.Column('validity_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=1000), nullable=False),
        sa.Column('situation', postgresql.ENUM('FILED', 'PUBLISHED', 'UNDER_EXAMINATION', 'OPPOSED', 'GRANTED', 'EXPIRED', 'LAPSED', 'RENEWED', name='processsituation', create_type=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_process_id'), 'process', ['id'], unique=False)
    op.create_index(op.f('ix_process_process_number'), 'process', ['process_number'], unique=True)
    
    # Criar tabela alert
    op.create_table(
        'alert',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('alert_type', postgresql.ENUM('mudanca_status', 'publicacao', 'prazo', 'processo_similar', 'renovacao_vencimento', name='alerttype', create_type=False), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_dismissed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['process_id'], ['process.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_id'), 'alert', ['id'], unique=False)
    
    # Criar tabela user_company_membership
    op.create_table(
        'user_company_membership',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', postgresql.ENUM('member', 'admin', 'owner', 'viewer', name='membershiprole', create_type=False), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'company_id')
    )
    
    # Criar tabela membership_history
    op.create_table(
        'membership_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('old_role', postgresql.ENUM('member', 'admin', 'owner', 'viewer', name='membershiprole', create_type=False), nullable=True),
        sa.Column('new_role', postgresql.ENUM('member', 'admin', 'owner', 'viewer', name='membershiprole', create_type=False), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('performed_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('performed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
        sa.ForeignKeyConstraint(['performed_by_user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_membership_history_id'), 'membership_history', ['id'], unique=False)
    
    # Criar tabela user_company_permission
    op.create_table(
        'user_company_permission',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission', postgresql.ENUM('read_processes', 'create_processes', 'update_processes', 'delete_processes', 'read_company_data', 'update_company_data', 'manage_users', 'view_reports', 'manage_billing', name='membershippermission', create_type=False), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('granted_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id', 'company_id'], ['user_company_membership.user_id', 'user_company_membership.company_id'], ),
        sa.ForeignKeyConstraint(['granted_by_user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_company_permission_id'), 'user_company_permission', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - remover todas as tabelas."""
    op.drop_table('user_company_permission')
    op.drop_table('membership_history')
    op.drop_table('user_company_membership')
    op.drop_table('alert')
    op.drop_table('process')
    op.drop_table('user_company_association')
    op.drop_table('company')
    op.drop_table('user')
    
    # Remover tipos ENUM
    op.execute('DROP TYPE IF EXISTS membershippermission CASCADE;')
    op.execute('DROP TYPE IF EXISTS membershiprole CASCADE;')
    op.execute('DROP TYPE IF EXISTS alerttype CASCADE;')
    op.execute('DROP TYPE IF EXISTS processsituation CASCADE;')
    op.execute('DROP TYPE IF EXISTS processtype CASCADE;')
    # ### end Alembic commands ###
