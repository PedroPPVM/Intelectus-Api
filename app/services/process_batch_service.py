import csv
import io
import logging
import time
import traceback
from typing import List
from uuid import UUID

import requests
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.crud_process_batch_job import process_batch_job as crud_batch_job
from app.db.session import SessionLocal
from app.models.process_batch_job import (
    BatchJobItemStatus,
    BatchJobStatus,
    ProcessBatchJob,
    ProcessBatchJobItem,
)
from app.models.user import User
from app.schemas.process import (
    ProcessCreate,
    ProcessTypeEnum,
)
from app.services.access_control_service import access_control_service
from app.services.inpi_pepi_service import inpi_pepi_service
from app.services.process_service import process_service

logger = logging.getLogger("intelectus.endpoints.processes.batch")


class ProcessBatchService:
    MAX_BYTES: int = 10 * 1024 * 1024

    def parse_csv(self, file_bytes: bytes) -> List[str]:
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("INVALID_ENCODING") from exc

        reader = csv.reader(io.StringIO(text), delimiter=",")
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]

        if rows:
            first_cell = rows[0][0].strip().lower() if rows[0] else ""
            if first_cell == "process_number":
                rows = rows[1:]

        numbers: List[str] = []
        for row in rows:
            if not row:
                continue
            value = row[0].strip()
            if value:
                numbers.append(value)

        if len(numbers) == 0:
            raise ValueError("EMPTY_CSV")

        return numbers

    def resolve_title(
        self, process_number: str, process_type: ProcessTypeEnum
    ) -> str:
        if process_type == ProcessTypeEnum.BRAND:
            data = inpi_pepi_service.lookup_marca(process_number)
            title = data.get("marca")
        elif process_type == ProcessTypeEnum.PATENT:
            data = inpi_pepi_service.lookup_patente(process_number)
            title = data.get("title")
        elif process_type == ProcessTypeEnum.SOFTWARE:
            data = inpi_pepi_service.lookup_programa(process_number)
            title = data.get("title")
        elif process_type == ProcessTypeEnum.DESIGN:
            data = inpi_pepi_service.lookup_desenho(process_number)
            title = data.get("title")
        else:
            raise ValueError(f"Tipo de processo não suportado: {process_type}")

        # ProcessCreate exige title com >= 5 chars; validamos antes para mapear o erro como NO_TITLE
        if not title or len(title.strip()) < 5:
            raise ValueError("NO_TITLE")

        return title.strip()

    def _classify_error(self, exc: Exception) -> tuple[str, str]:
        if isinstance(exc, HTTPException):
            detail = str(exc.detail) if exc.detail is not None else ""
            if exc.status_code == status.HTTP_400_BAD_REQUEST and "já está cadastrado" in detail:
                return "DUPLICATE", detail[:200]
            if exc.status_code == status.HTTP_400_BAD_REQUEST:
                return "VALIDATION", detail[:200]
            if exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                return "VALIDATION", detail[:200]
            return "INTERNAL", detail[:200]

        if isinstance(exc, ValueError):
            message = str(exc)
            if message == "NO_TITLE":
                return "NO_TITLE", "Título não disponível no INPI"
            if "não encontrad" in message.lower():
                return "NOT_FOUND", message[:200]
            return "VALIDATION", message[:200]

        if isinstance(exc, (requests.ConnectionError, requests.Timeout, requests.HTTPError)):
            return "INPI_UNAVAILABLE", "INPI pePI indisponível"

        return "INTERNAL", str(exc)[:200]

    def enqueue_job(
        self,
        db: Session,
        *,
        company_id: UUID,
        process_type: ProcessTypeEnum,
        process_numbers: List[str],
        user: User,
        background_tasks: BackgroundTasks,
    ) -> ProcessBatchJob:
        access_control_service.validate_company_access(
            db, user, company_id, "create_processes"
        )

        job = crud_batch_job.create_job(
            db,
            company_id=company_id,
            user_id=user.id,
            process_type=process_type,
            process_numbers=process_numbers,
        )

        logger.info(
            f"batch_enqueue job_id={job.id} company_id={company_id} "
            f"type={process_type.value} rows={len(process_numbers)} user_id={user.id}"
        )

        background_tasks.add_task(self.run_job, job.id)
        return job

    def run_job(self, job_id: UUID) -> None:
        # Worker isolado: abre sessão própria, comita por item para visibilidade incremental.
        db: Session = SessionLocal()
        started_at = time.monotonic()
        try:
            job = crud_batch_job.get_job(db, job_id)
            if job is None:
                logger.error(f"batch_run_missing job_id={job_id}")
                return

            process_type = ProcessTypeEnum(job.process_type.value)
            company_id = job.company_id

            crud_batch_job.mark_running(db, job)
            logger.info(f"batch_run_start job_id={job.id} rows={job.total_rows}")

            user = db.query(User).filter(User.id == job.created_by_user_id).first()
            if user is None:
                crud_batch_job.mark_finished(
                    db,
                    job,
                    final_status=BatchJobStatus.FAILED,
                    error="Usuário criador do job não encontrado",
                )
                logger.error(f"batch_run_no_user job_id={job.id}")
                return

            try:
                items = crud_batch_job.list_pending_items(db, job.id)
                for item in items:
                    self._process_item(
                        db,
                        job_id=job.id,
                        item_id=item.id,
                        process_number=item.process_number,
                        row_index=item.row_index,
                        process_type=process_type,
                        company_id=company_id,
                        user=user,
                    )

                db.refresh(job)
                final_status = (
                    BatchJobStatus.COMPLETED_WITH_ERRORS
                    if job.failed_count > 0
                    else BatchJobStatus.COMPLETED
                )
                crud_batch_job.mark_finished(db, job, final_status=final_status)
            except Exception as exc:
                db.rollback()
                logger.error(
                    f"batch_run_crashed job_id={job.id} error={exc}\n"
                    f"{traceback.format_exc()}"
                )
                try:
                    job_refresh = crud_batch_job.get_job(db, job_id)
                    if job_refresh is not None:
                        crud_batch_job.mark_finished(
                            db,
                            job_refresh,
                            final_status=BatchJobStatus.FAILED,
                            error=str(exc)[:500],
                        )
                except Exception:
                    logger.error(
                        f"batch_run_finish_failed job_id={job_id}\n{traceback.format_exc()}"
                    )

            duration_ms = int((time.monotonic() - started_at) * 1000)
            db.refresh(job)
            logger.info(
                f"batch_run_done job_id={job.id} status={job.status.value} "
                f"created={job.created_count} failed={job.failed_count} "
                f"duration_ms={duration_ms}"
            )
        finally:
            db.close()

    def _process_item(
        self,
        db: Session,
        *,
        job_id: UUID,
        item_id: UUID,
        process_number: str,
        row_index: int,
        process_type: ProcessTypeEnum,
        company_id: UUID,
        user: User,
    ) -> None:
        item = (
            db.query(ProcessBatchJobItem)
            .filter(ProcessBatchJobItem.id == item_id)
            .first()
        )
        # Idempotência: se o item já foi processado em uma execução anterior, ignorar.
        if item is None or item.status != BatchJobItemStatus.PENDING:
            return

        try:
            title = self.resolve_title(process_number, process_type)
            process_data = ProcessCreate(
                process_type=process_type,
                process_number=process_number,
                title=title,
                company_id=company_id,
            )
            process = process_service.create_process_with_validation(
                db, process_data, company_id, user
            )
            crud_batch_job.update_item_success(
                db, item, process_id=process.id, title=title
            )
            crud_batch_job.increment_counters(
                db, job_id, created_delta=1, failed_delta=0
            )
            logger.info(
                f"batch_item_ok job_id={job_id} row={row_index} "
                f"process_number={process_number} process_id={process.id}"
            )
        except Exception as exc:
            db.rollback()
            error_code, error_message = self._classify_error(exc)
            if error_code == "INTERNAL":
                logger.warning(
                    f"batch_item_fail job_id={job_id} row={row_index} "
                    f"process_number={process_number} error_code={error_code} "
                    f"error={error_message}\n{traceback.format_exc()}"
                )
            else:
                logger.warning(
                    f"batch_item_fail job_id={job_id} row={row_index} "
                    f"process_number={process_number} error_code={error_code} "
                    f"error={error_message}"
                )
            item = (
                db.query(ProcessBatchJobItem)
                .filter(ProcessBatchJobItem.id == item_id)
                .first()
            )
            if item is not None:
                crud_batch_job.update_item_failure(
                    db, item, error_code=error_code, error=error_message
                )
                crud_batch_job.increment_counters(
                    db, job_id, created_delta=0, failed_delta=1
                )

    def reconcile_orphans(self) -> int:
        # Hook de startup: jobs em RUNNING após restart indicam crash do worker anterior.
        db: Session = SessionLocal()
        try:
            orphans = crud_batch_job.find_orphan_running(db)
            for job in orphans:
                logger.warning(f"batch_reconcile_orphan job_id={job.id}")
                crud_batch_job.mark_finished(
                    db,
                    job,
                    final_status=BatchJobStatus.FAILED,
                    error="Worker crashed before completion",
                )
            return len(orphans)
        finally:
            db.close()


process_batch_service = ProcessBatchService()
