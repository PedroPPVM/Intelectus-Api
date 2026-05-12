from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.process_batch_job import (
    BatchJobItemStatus,
    BatchJobStatus,
    ProcessBatchJob,
    ProcessBatchJobItem,
)
from app.schemas.process import ProcessTypeEnum


class CRUDProcessBatchJob:
    def create_job(
        self,
        db: Session,
        *,
        company_id: UUID,
        user_id: UUID,
        process_type: ProcessTypeEnum,
        process_numbers: List[str],
    ) -> ProcessBatchJob:
        from app.models.process import ProcessType

        job = ProcessBatchJob(
            company_id=company_id,
            created_by_user_id=user_id,
            process_type=ProcessType(process_type.value),
            status=BatchJobStatus.PENDING,
            total_rows=len(process_numbers),
            processed_rows=0,
            created_count=0,
            failed_count=0,
        )
        db.add(job)
        db.flush()

        items = [
            ProcessBatchJobItem(
                job_id=job.id,
                row_index=idx,
                process_number=number,
                status=BatchJobItemStatus.PENDING,
            )
            for idx, number in enumerate(process_numbers)
        ]
        db.add_all(items)
        db.commit()
        db.refresh(job)
        return job

    def get_job(self, db: Session, job_id: UUID) -> Optional[ProcessBatchJob]:
        return (
            db.query(ProcessBatchJob)
            .filter(ProcessBatchJob.id == job_id)
            .first()
        )

    def list_items(
        self,
        db: Session,
        job_id: UUID,
        *,
        skip: int,
        limit: int,
        status_filter: Optional[BatchJobItemStatus] = None,
    ) -> Tuple[List[ProcessBatchJobItem], int]:
        query = db.query(ProcessBatchJobItem).filter(
            ProcessBatchJobItem.job_id == job_id
        )
        if status_filter is not None:
            query = query.filter(ProcessBatchJobItem.status == status_filter)

        total = query.count()
        items = (
            query.order_by(ProcessBatchJobItem.row_index.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def list_pending_items(
        self, db: Session, job_id: UUID
    ) -> List[ProcessBatchJobItem]:
        return (
            db.query(ProcessBatchJobItem)
            .filter(
                ProcessBatchJobItem.job_id == job_id,
                ProcessBatchJobItem.status == BatchJobItemStatus.PENDING,
            )
            .order_by(ProcessBatchJobItem.row_index.asc())
            .all()
        )

    def mark_running(self, db: Session, job: ProcessBatchJob) -> None:
        job.status = BatchJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()

    def mark_finished(
        self,
        db: Session,
        job: ProcessBatchJob,
        *,
        final_status: BatchJobStatus,
        error: Optional[str] = None,
    ) -> None:
        job.status = final_status
        job.finished_at = datetime.now(timezone.utc)
        if error is not None:
            job.error = error[:500]
        db.add(job)
        db.commit()

    def update_item_success(
        self,
        db: Session,
        item: ProcessBatchJobItem,
        *,
        process_id: UUID,
        title: str,
    ) -> None:
        item.status = BatchJobItemStatus.CREATED
        item.process_id = process_id
        item.title = title
        item.error = None
        item.error_code = None
        db.add(item)
        db.commit()

    def update_item_failure(
        self,
        db: Session,
        item: ProcessBatchJobItem,
        *,
        error_code: str,
        error: str,
    ) -> None:
        item.status = BatchJobItemStatus.FAILED
        item.error_code = error_code[:32] if error_code else None
        item.error = error[:200] if error else None
        db.add(item)
        db.commit()

    def increment_counters(
        self,
        db: Session,
        job_id: UUID,
        *,
        created_delta: int = 0,
        failed_delta: int = 0,
    ) -> None:
        stmt = (
            update(ProcessBatchJob)
            .where(ProcessBatchJob.id == job_id)
            .values(
                processed_rows=ProcessBatchJob.processed_rows + 1,
                created_count=ProcessBatchJob.created_count + created_delta,
                failed_count=ProcessBatchJob.failed_count + failed_delta,
            )
        )
        db.execute(stmt)
        db.commit()

    def find_orphan_running(self, db: Session) -> List[ProcessBatchJob]:
        return (
            db.query(ProcessBatchJob)
            .filter(ProcessBatchJob.status == BatchJobStatus.RUNNING)
            .all()
        )


process_batch_job = CRUDProcessBatchJob()
