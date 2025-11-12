"""Add missing enum values for processtype and processstatus

Revision ID: enum_fix_001
Revises: c8885d61a1f1
Create Date: 2025-07-20 21:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'enum_fix_001'
down_revision = 'c8885d61a1f1'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing enum values."""
    
    connection = op.get_bind()
    
    # Verificar se o enum processtype existe antes de adicionar valores
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_type 
            WHERE typname = 'processtype'
        );
    """))
    
    if result.scalar():
        # Add missing ProcessType values
        try:
            op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'marca'")
        except Exception:
            pass  # Valor pode já existir
        try:
            op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'patente'")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'desenho_industrial'")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'programa_computador'")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'modelo_utilidade'")
        except Exception:
            pass
    
    # Verificar se o enum processstatus existe antes de adicionar valores
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM pg_type 
            WHERE typname = 'processstatus'
        );
    """))
    
    if result.scalar():
        # Add missing ProcessStatus values
        try:
            op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'pendente'")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'ativo'")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'deferido'")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'indeferido'")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'expirado'")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'abandonado'")
        except Exception:
            pass


def downgrade():
    """Cannot remove enum values in PostgreSQL."""
    pass
