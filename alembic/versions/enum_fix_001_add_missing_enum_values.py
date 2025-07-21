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
    
    # Add missing ProcessType values
    op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'marca'")
    op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'patente'")  
    op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'desenho_industrial'")
    op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'programa_computador'")
    op.execute("ALTER TYPE processtype ADD VALUE IF NOT EXISTS 'modelo_utilidade'")
    
    # Add missing ProcessStatus values
    op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'pendente'")
    op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'ativo'")
    op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'deferido'")
    op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'indeferido'")
    op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'expirado'")
    op.execute("ALTER TYPE processstatus ADD VALUE IF NOT EXISTS 'abandonado'")


def downgrade():
    """Cannot remove enum values in PostgreSQL."""
    pass
