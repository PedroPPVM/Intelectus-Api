"""add process_batch_job tables

Revision ID: d1e2f3a4b5c6
Revises: f1a2b3c4d5e6
Create Date: 2026-04-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    batch_job_status = postgresql.ENUM(
        'PENDING', 'RUNNING', 'COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED',
        name='batchjobstatus',
        create_type=True,
    )
    batch_job_status.create(op.get_bind(), checkfirst=True)

    batch_job_item_status = postgresql.ENUM(
        'PENDING', 'CREATED', 'FAILED',
        name='batchjobitemstatus',
        create_type=True,
    )
    batch_job_item_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'process_batch_job',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'company_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('company.id'),
            nullable=False,
        ),
        sa.Column(
            'created_by_user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('user.id'),
            nullable=False,
        ),
        sa.Column(
            'process_type',
            postgresql.ENUM(
                'BRAND', 'PATENT', 'DESIGN', 'SOFTWARE',
                name='processtype', create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            'status',
            postgresql.ENUM(
                'PENDING', 'RUNNING', 'COMPLETED',
                'COMPLETED_WITH_ERRORS', 'FAILED',
                name='batchjobstatus', create_type=False,
            ),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('total_rows', sa.Integer(), nullable=False),
        sa.Column('processed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_process_batch_job_company_id', 'process_batch_job', ['company_id']
    )
    op.create_index(
        'ix_process_batch_job_created_by_user_id',
        'process_batch_job',
        ['created_by_user_id'],
    )
    op.create_index(
        'ix_process_batch_job_status', 'process_batch_job', ['status']
    )

    op.create_table(
        'process_batch_job_item',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'job_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('process_batch_job.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('process_number', sa.String(length=50), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM(
                'PENDING', 'CREATED', 'FAILED',
                name='batchjobitemstatus', create_type=False,
            ),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column(
            'process_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('process.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('title', sa.String(length=1000), nullable=True),
        sa.Column('error', sa.String(length=200), nullable=True),
        sa.Column('error_code', sa.String(length=32), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('job_id', 'row_index', name='uq_batch_item_job_row'),
    )
    op.create_index(
        'ix_process_batch_job_item_job_id',
        'process_batch_job_item',
        ['job_id'],
    )
    op.create_index(
        'ix_process_batch_job_item_status',
        'process_batch_job_item',
        ['status'],
    )
    op.create_index(
        'ix_batch_item_job_status',
        'process_batch_job_item',
        ['job_id', 'status'],
    )


def downgrade() -> None:
    op.drop_index('ix_batch_item_job_status', table_name='process_batch_job_item')
    op.drop_index(
        'ix_process_batch_job_item_status', table_name='process_batch_job_item'
    )
    op.drop_index(
        'ix_process_batch_job_item_job_id', table_name='process_batch_job_item'
    )
    op.drop_table('process_batch_job_item')

    op.drop_index('ix_process_batch_job_status', table_name='process_batch_job')
    op.drop_index(
        'ix_process_batch_job_created_by_user_id',
        table_name='process_batch_job',
    )
    op.drop_index(
        'ix_process_batch_job_company_id', table_name='process_batch_job'
    )
    op.drop_table('process_batch_job')

    bind = op.get_bind()
    postgresql.ENUM(name='batchjobitemstatus').drop(bind, checkfirst=True)
    postgresql.ENUM(name='batchjobstatus').drop(bind, checkfirst=True)
