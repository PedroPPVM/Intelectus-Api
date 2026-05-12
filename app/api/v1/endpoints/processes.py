from typing import List, Literal, Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, status, Query, UploadFile
from sqlalchemy.orm import Session

from app.crud.crud_process_batch_job import process_batch_job as crud_batch_job
from app.db.session import get_db
from app.models.process_batch_job import BatchJobItemStatus
from app.models.user import User
from app.schemas.process import (
    BatchJobItemsPage,
    BatchJobStatusEnum,
    BatchProcessItemResult,
    BatchProcessJobAccepted,
    BatchProcessJobResponse,
    ProcessCreate, ProcessUpdate, ProcessResponse, ProcessSummary,
    ProcessTypeEnum
)
from app.security.auth import get_current_user
from app.services.process_service import process_service
from app.services.process_batch_service import process_batch_service
from app.services.access_control_service import access_control_service


ALLOWED_CSV_CONTENT_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/csv",
    "application/octet-stream",
}


router = APIRouter()


@router.post("/", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
def create_process(
    *,
    db: Session = Depends(get_db),
    process_in: ProcessCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Criar um novo processo - REFATORADO COM SERVICES.
    
    💡 Use este endpoint quando você não está no contexto de uma empresa específica.
    Para operações company-oriented, prefira `/companies/{company_id}/processes/` para melhor performance.
    
    Refatorado para usar ProcessService com todas as validações.
    """
    # Usar ProcessService com todas as validações
    process = process_service.create_process_with_validation(
        db, process_in, process_in.company_id, current_user
    )
    
    return ProcessResponse.model_validate(process)


@router.get("/", response_model=List[ProcessSummary])
def read_processes(
    skip: int = 0,
    limit: int = 100,
    company_id: Optional[UUID] = Query(None, description="Filtrar por empresa"),
    process_type: Optional[ProcessTypeEnum] = Query(None, description="Filtrar por tipo"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por status"),
    title: Optional[str] = Query(None, description="Buscar no título"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar processos - REFATORADO COM SERVICES.
    
    💡 Use este endpoint para listar processos de TODAS as empresas do usuário.
    Para processos de uma empresa específica, prefira `/companies/{company_id}/processes/` 
    que oferece melhor performance com índices otimizados.
    
    Refatorado para usar Services com validações centralizadas.
    """
    if company_id:
        # Se company_id especificado, usar ProcessService otimizado
        filters = {
            'skip': skip,
            'limit': limit,
            'process_type': process_type.value if process_type else None,
            'status': status_filter if status_filter else None,
            'title': title
        }
        
        processes = process_service.get_company_processes_with_filters(
            db, company_id, current_user, filters
        )
    else:
        # Fallback para AccessControlService (menos otimizado)
        processes = access_control_service.get_user_accessible_processes(
            db, current_user, skip, limit
        )
        
        # Aplicar filtros manualmente (legacy behavior)
        if process_type:
            processes = [p for p in processes if p.process_type.value == process_type.value]
        if status_filter:
            processes = [p for p in processes if p.status == status_filter]
        if title:
            processes = [p for p in processes if title.lower() in p.title.lower()]
    
    # Usar ProcessService para transformação padronizada
    summary_data = process_service.transform_to_process_summary(processes)
    
    return summary_data


@router.get("/{process_id}", response_model=ProcessResponse)
def read_process(
    process_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obter dados de um processo específico - REFATORADO COM SERVICES.
    
    💡 Use este endpoint quando você conhece apenas o ID do processo.
    Para processos no contexto de uma empresa, prefira 
    `/companies/{company_id}/processes/{process_id}` para melhor performance.
    
    Refatorado para usar AccessControlService com validações centralizadas.
    """
    # Usar AccessControlService para validação centralizada
    process = access_control_service.validate_process_access(
        db, current_user, process_id, "read_processes"
    )
    
    return ProcessResponse.model_validate(process)


@router.put("/{process_id}", response_model=ProcessResponse)
def update_process(
    process_id: UUID,
    process_in: ProcessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualizar dados de um processo - REFATORADO COM SERVICES.
    
    💡 Use este endpoint quando você conhece apenas o ID do processo.
    Para atualizações no contexto de uma empresa, prefira 
    `/companies/{company_id}/processes/{process_id}` para melhor performance.
    
    Refatorado para usar ProcessService com validações completas.
    """
    # Primeiro buscar processo para obter company_id
    process = access_control_service.validate_process_access(
        db, current_user, process_id, "update_processes"
    )
    
    # Usar ProcessService com company_id obtido
    updated_process = process_service.update_process_with_validation(
        db, process_id, process_in, process.company_id, current_user
    )
    
    return ProcessResponse.model_validate(updated_process)


@router.delete("/{process_id}")
def delete_process(
    process_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletar um processo - REFATORADO COM SERVICES.
    
    💡 Use este endpoint quando você conhece apenas o ID do processo.
    Para exclusões no contexto de uma empresa, prefira 
    `/companies/{company_id}/processes/{process_id}` para melhor performance.
    
    Refatorado para usar ProcessService com validações completas.
    """
    # Primeiro buscar processo para obter company_id
    process = access_control_service.validate_process_access(
        db, current_user, process_id, "delete_processes"
    )
    
    # Usar ProcessService com company_id obtido
    process_service.delete_process_with_validation(
        db, process_id, process.company_id, current_user
    )
    
    return {"message": "Processo deletado com sucesso"}


@router.get("/number/{process_number}", response_model=ProcessResponse)
def read_process_by_number(
    process_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Buscar processo por número - REFATORADO COM SERVICES.
    
    💡 Use este endpoint para buscar processo quando você não sabe de qual empresa ele é.
    Para buscas no contexto de uma empresa, prefira 
    `/companies/{company_id}/processes/number/{process_number}` que usa índices otimizados.
    
    Refatorado para usar AccessControlService com validações centralizadas.
    """
    # Buscar processo usando CRUD (não otimizado, sem índice por empresa)
    from app.crud import process as crud_process
    process = crud_process.get_by_number(db, process_number=process_number)
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processo não encontrado"
        )
    
    # Usar AccessControlService para validação
    access_control_service.validate_process_access(
        db, current_user, process.id, "read_processes"
    )
    
    return ProcessResponse.model_validate(process)


@router.patch("/{process_id}/scraped", response_model=ProcessResponse)
def mark_process_scraped(
    process_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marcar processo como recém-scrapado - REFATORADO COM SERVICES.
    
    Endpoint interno para o sistema de scraping com auditoria completa.
    """
    # Usar ProcessService com validação e auditoria
    updated_process = process_service.mark_process_scraped_with_audit(
        db, process_id, current_user
    )
    
    return ProcessResponse.model_validate(updated_process) 


@router.patch("/{process_id}/scrape-status")
def scrape_status_process(
    process_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualiza o status do processo a partir da revista RPI mais recente via scraping.
    """
    # Buscar processo e validar acesso
    process = access_control_service.validate_process_access(
        db, current_user, process_id, "update_processes"
    )
    # Chamar o serviço de scraping
    from app.services.scraping_service import scraping_service
    result = scraping_service.scrape_and_update_process(
        db=db,
        process_number=process.process_number,
        process_type=process.process_type,
        company_id=process.company_id
    )
    return result


_ITEM_STATUS_MAP = {
    "pending": BatchJobItemStatus.PENDING,
    "created": BatchJobItemStatus.CREATED,
    "failed": BatchJobItemStatus.FAILED,
}

_ITEM_STATUS_OUT = {
    BatchJobItemStatus.PENDING: "pending",
    BatchJobItemStatus.CREATED: "created",
    BatchJobItemStatus.FAILED: "failed",
}


def _build_status_url(job_id: UUID) -> str:
    return f"/api/v1/processes/batch-jobs/{job_id}"


def _build_items_url(job_id: UUID) -> str:
    return f"/api/v1/processes/batch-jobs/{job_id}/items"


@router.post(
    "/batch-csv",
    response_model=BatchProcessJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_processes_batch_csv(
    background_tasks: BackgroundTasks,
    company_id: UUID = Form(...),
    process_type: ProcessTypeEnum = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cria um job assíncrono para processar em lote um CSV de `process_number`.
    Retorna 202 com `job_id`; cliente acompanha via `GET /batch-jobs/{job_id}`.
    """
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()

    if not (filename.endswith(".csv") or content_type in ALLOWED_CSV_CONTENT_TYPES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Arquivo deve ser CSV (.csv)",
        )

    content = file.file.read(process_batch_service.MAX_BYTES + 1)
    if len(content) > process_batch_service.MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo excede o limite de {process_batch_service.MAX_BYTES} bytes",
        )

    try:
        numbers = process_batch_service.parse_csv(content)
    except ValueError as exc:
        code = str(exc)
        if code == "EMPTY_CSV":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV vazio ou sem linhas úteis",
            )
        if code == "INVALID_ENCODING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV inválido: falha ao decodificar como UTF-8",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV inválido: {code}",
        )

    job = process_batch_service.enqueue_job(
        db,
        company_id=company_id,
        process_type=process_type,
        process_numbers=numbers,
        user=current_user,
        background_tasks=background_tasks,
    )

    return BatchProcessJobAccepted(
        job_id=job.id,
        status=BatchJobStatusEnum(job.status.value),
        total_rows=job.total_rows,
        company_id=job.company_id,
        process_type=ProcessTypeEnum(job.process_type.value),
        created_at=job.created_at,
        status_url=_build_status_url(job.id),
        items_url=_build_items_url(job.id),
    )


@router.get(
    "/batch-jobs/{job_id}",
    response_model=BatchProcessJobResponse,
)
def get_batch_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = crud_batch_job.get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado",
        )

    access_control_service.validate_company_access(
        db, current_user, job.company_id, "read_processes"
    )

    return BatchProcessJobResponse(
        id=job.id,
        company_id=job.company_id,
        process_type=ProcessTypeEnum(job.process_type.value),
        status=BatchJobStatusEnum(job.status.value),
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        created_count=job.created_count,
        failed_count=job.failed_count,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_by_user_id=job.created_by_user_id,
        items_url=_build_items_url(job.id),
    )


@router.get(
    "/batch-jobs/{job_id}/items",
    response_model=BatchJobItemsPage,
)
def get_batch_job_items(
    job_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[Literal["pending", "created", "failed"]] = Query(
        None, alias="status"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = crud_batch_job.get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado",
        )

    access_control_service.validate_company_access(
        db, current_user, job.company_id, "read_processes"
    )

    item_status = _ITEM_STATUS_MAP.get(status_filter) if status_filter else None
    items, total = crud_batch_job.list_items(
        db, job_id, skip=skip, limit=limit, status_filter=item_status
    )

    payload_items: List[BatchProcessItemResult] = [
        BatchProcessItemResult(
            process_number=item.process_number,
            status=_ITEM_STATUS_OUT[item.status],
            process_id=item.process_id,
            title=item.title,
            error=item.error,
            error_code=item.error_code,
            row_index=item.row_index,
        )
        for item in items
    ]

    return BatchJobItemsPage(
        job_id=job.id,
        total=total,
        skip=skip,
        limit=limit,
        items=payload_items,
    )
