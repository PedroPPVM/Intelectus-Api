from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.process import (
    ProcessCreate, ProcessUpdate, ProcessResponse, ProcessSummary,
    ProcessTypeEnum, ProcessStatusEnum
)
from app.security.auth import get_current_user
from app.services.process_service import process_service
from app.services.access_control_service import access_control_service


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
    status_filter: Optional[ProcessStatusEnum] = Query(None, alias="status", description="Filtrar por status"),
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
            'status': status_filter.value if status_filter else None,
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
            processes = [p for p in processes if p.status.value == status_filter.value]
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