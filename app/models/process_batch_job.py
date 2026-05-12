import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.process import ProcessType


class BatchJobStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class BatchJobItemStatus(enum.Enum):
    PENDING = "PENDING"
    CREATED = "CREATED"
    FAILED = "FAILED"


class ProcessBatchJob(Base):
    __tablename__ = "process_batch_job"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("company.id"), nullable=False, index=True
    )
    created_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False, index=True
    )
    process_type = Column(
        Enum(ProcessType, name="processtype", native_enum=True, create_type=False),
        nullable=False,
    )
    status = Column(
        Enum(BatchJobStatus, name="batchjobstatus", native_enum=True),
        nullable=False,
        default=BatchJobStatus.PENDING,
        index=True,
    )
    total_rows = Column(Integer, nullable=False)
    processed_rows = Column(Integer, nullable=False, default=0)
    created_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    items = relationship(
        "ProcessBatchJobItem",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="ProcessBatchJobItem.row_index",
    )


class ProcessBatchJobItem(Base):
    __tablename__ = "process_batch_job_item"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("process_batch_job.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_index = Column(Integer, nullable=False)
    process_number = Column(String(50), nullable=False)
    status = Column(
        Enum(BatchJobItemStatus, name="batchjobitemstatus", native_enum=True),
        nullable=False,
        default=BatchJobItemStatus.PENDING,
        index=True,
    )
    process_id = Column(
        UUID(as_uuid=True),
        ForeignKey("process.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = Column(String(1000), nullable=True)
    error = Column(String(200), nullable=True)
    error_code = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    job = relationship("ProcessBatchJob", back_populates="items")

    __table_args__ = (
        UniqueConstraint("job_id", "row_index", name="uq_batch_item_job_row"),
        Index("ix_batch_item_job_status", "job_id", "status"),
    )
