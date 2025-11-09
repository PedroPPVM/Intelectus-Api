from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse, AlertTypeEnum
from app.security.auth import get_current_user, get_current_superuser
from app.services.alert_service import alert_service
from app.services.access_control_service import access_control_service
from app.crud import alert as crud_alert


router = APIRouter()


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    *,
    db: Session = Depends(get_db),
    alert_in: AlertCreate,
    current_user: User = Depends(get_current_superuser)  # Apenas superusuários criam alertas
):
    """
    Criar um novo alerta - REFATORADO COM SERVICES.
    
    Usa AlertService para centralizar validações e criação.
    """
    # Usar AlertService com todas as validações
    alert = alert_service.create_alert_with_validation(
        db, alert_in, current_user
    )
    
    return AlertResponse.model_validate(alert)


@router.get("/", response_model=List[AlertResponse])
def read_alerts(
    skip: int = 0,
    limit: int = 100,
    unread_only: bool = Query(False, description="Mostrar apenas alertas não lidos"),
    alert_type: Optional[AlertTypeEnum] = Query(None, description="Filtrar por tipo de alerta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar alertas do usuário atual - REFATORADO COM SERVICES.
    
    Usa AlertService para centralizar lógicas de acesso e filtros.
    """
    # Usar AlertService com filtros centralizados
    filters = {
        'skip': skip,
        'limit': limit,
        'unread_only': unread_only,
        'alert_type': alert_type.value if alert_type else None
    }
    
    alerts = alert_service.get_user_alerts_with_filters(
        db, current_user, filters
    )
    
    return [AlertResponse.model_validate(alert) for alert in alerts]


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obter número de alertas não lidos do usuário atual.
    
    REFATORADO: Mantido uso direto de CRUD pois é operação simples de contagem.
    Para operações mais complexas, usar AlertService.
    """
    count = crud_alert.count_unread_by_user(db, user_id=current_user.id)
    
    return {"unread_count": count}


@router.get("/{alert_id}", response_model=AlertResponse)
def read_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obter dados de um alerta específico - REFATORADO COM SERVICES.
    
    Usa AlertService para validação de acesso centralizada.
    """
    # Usar AlertService para validação e busca
    alert = alert_service.get_alert_with_access_validation(
        db, alert_id, current_user
    )
    
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}/read", response_model=AlertResponse)
def mark_alert_read(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marcar alerta como lido - REFATORADO COM SERVICES.
    
    Usa AlertService para validação e auditoria centralizadas.
    """
    # Usar AlertService com validação e auditoria
    updated_alert = alert_service.mark_alert_as_read_with_audit(
        db, alert_id, current_user
    )
    
    return AlertResponse.model_validate(updated_alert)


@router.patch("/{alert_id}/dismiss", response_model=AlertResponse)
def dismiss_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marcar alerta como descartado - REFATORADO COM SERVICES.
    
    Usa AlertService para validação e auditoria centralizadas.
    """
    # Usar AlertService com validação e auditoria
    updated_alert = alert_service.mark_alert_as_dismissed_with_audit(
        db, alert_id, current_user
    )
    
    return AlertResponse.model_validate(updated_alert)


@router.post("/mark-all-read")
def mark_all_alerts_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marcar todos os alertas do usuário como lidos.
    
    REFATORADO: Usa AlertService para operação padronizada.
    """
    count = alert_service.mark_all_user_alerts_as_read(db, current_user)
    
    return {"message": f"{count} alertas marcados como lidos"}


@router.get("/process/{process_id}", response_model=List[AlertResponse])
def read_process_alerts(
    process_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar alertas relacionados a um processo específico - REFATORADO COM SERVICES.
    
    Usa AlertService para centralizar validações de acesso ao processo.
    """
    # Usar AlertService com validação de acesso completa
    alerts = alert_service.get_process_related_alerts(
        db, process_id, current_user, skip, limit
    )
    
    return [AlertResponse.model_validate(alert) for alert in alerts]


@router.put("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: UUID,
    alert_in: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualizar um alerta - REFATORADO COM SERVICES.
    
    Usa AlertService para validação centralizada.
    """
    # Usar AlertService com validação
    updated_alert = alert_service.update_alert_with_validation(
        db, alert_id, alert_in, current_user
    )
    
    return AlertResponse.model_validate(updated_alert)


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletar um alerta - REFATORADO COM SERVICES.
    
    Usa AlertService para validação centralizada.
    """
    # Usar AlertService com validação
    alert_service.delete_alert_with_validation(
        db, alert_id, current_user
    )
    
    return {"message": "Alerta deletado com sucesso"}


@router.delete("/cleanup/old")
def cleanup_old_alerts(
    days: int = Query(30, description="Deletar alertas descartados mais antigos que X dias"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)  # Apenas superusuários
):
    """
    Deletar alertas antigos e descartados (limpeza do sistema).
    """
    count = crud_alert.delete_old_alerts(db, days=days)
    
    return {"message": f"{count} alertas antigos deletados"} 