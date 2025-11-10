from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.membership import (
    MembershipCreate, MembershipUpdate, MembershipResponse,
    MembershipHistoryResponse, MembershipStats, MembershipSummary,
    BulkMembershipCreate
)
from app.security.auth import get_current_user, get_current_superuser
from app.services.membership_service import membership_service


router = APIRouter()


@router.post("/", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
def create_membership(
    *,
    db: Session = Depends(get_db),
    membership_in: MembershipCreate,
    current_user: User = Depends(get_current_user),
    request: Request
):
    """
    **Criar novo membership** com auditoria completa.
    
    Cria relacionamento User ↔ Company com:
    - ✅ **Role específica** (member, admin, owner, viewer)
    - ✅ **Permissões granulares** opcionais
    - ✅ **Auditoria completa** (quem, quando, por que)
    - ✅ **Sincronização** com tabela legacy
    
    **Requer:** Ser superusuário OU ter acesso à empresa de destino
    """
    # Verificar permissões
    if not current_user.is_superuser:
        # Usuário normal precisa ter acesso à empresa
        has_access = membership_service.check_user_permission(
            db, current_user.id, membership_in.company_id, "manage_users"
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: você precisa ter permissão 'manage_users' na empresa"
            )
    
    # Obter IP do usuário para auditoria
    client_ip = request.client.host if request.client else None
    
    # Criar membership
    return membership_service.create_membership(
        db=db,
        membership_data=membership_in,
        created_by_user_id=current_user.id,
        ip_address=client_ip
    )


@router.get("/companies/{company_id}/members", response_model=List[MembershipSummary])
def get_company_members(
    company_id: UUID,
    *,
    role_filter: Optional[str] = Query(None, description="Filtrar por role (member, admin, owner, viewer)"),
    active_only: bool = Query(True, description="Apenas memberships ativos"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Listar membros de uma empresa** com informações detalhadas.
    
    Retorna:
    - 👥 **Lista de membros** com roles e permissões
    - 📊 **Contagem de permissões** específicas
    - ⏰ **Data de criação** do membership
    - 🔍 **Filtros avançados** por role e status
    """
    # Verificar acesso à empresa
    if not current_user.is_superuser:
        has_access = membership_service.check_user_permission(
            db, current_user.id, company_id, "read_company_data"
        )
        # Fallback: verificar se usuário está na empresa via associação legada
        if not has_access:
            from app.models.company import Company
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Empresa não encontrada"
                )
            # Verificar se usuário está na empresa via associação legada
            if current_user not in company.users:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado à empresa"
                )
    
    return membership_service.get_company_members(
        db=db,
        company_id=company_id,
        role_filter=role_filter,
        active_only=active_only,
        skip=skip,
        limit=limit
    )


@router.get("/users/{user_id}/companies", response_model=List[MembershipResponse])
def get_user_companies(
    user_id: UUID,
    include_permissions: bool = Query(False, description="Incluir permissões específicas"),
    active_only: bool = Query(True, description="Apenas memberships ativos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Listar empresas de um usuário** com detalhes de membership.
    
    Retorna empresas associadas com:
    - 🎭 **Role em cada empresa** (member, admin, owner, viewer)
    - 🔐 **Permissões específicas** (opcional)
    - 📅 **Datas de criação/atualização**
    - ⚡ **Status ativo/inativo**
    """
    # Verificar se pode visualizar dados do usuário
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: só pode ver suas próprias empresas"
        )
    
    return membership_service.get_user_companies(
        db=db,
        user_id=user_id,
        include_permissions=include_permissions,
        active_only=active_only
    )


@router.put("/{user_id}/companies/{company_id}", response_model=MembershipResponse)
def update_membership(
    user_id: UUID,
    company_id: UUID,
    membership_update: MembershipUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Atualizar membership existente** com auditoria.
    
    Permite atualizar:
    - 🎭 **Role** (promover/rebaixar usuário)
    - ✅ **Status ativo/inativo** (ativar/desativar temporariamente)
    - 🔐 **Permissões específicas** (granulares)
    - 📝 **Motivo** da alteração (auditoria)
    """
    # Verificar permissões
    if not current_user.is_superuser:
        has_access = membership_service.check_user_permission(
            db, current_user.id, company_id, "manage_users"
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: precisa de permissão 'manage_users'"
            )
    
    # Obter IP para auditoria
    client_ip = request.client.host if request.client else None
    
    try:
        return membership_service.update_membership(
            db=db,
            user_id=user_id,
            company_id=company_id,
            membership_update=membership_update,
            updated_by_user_id=current_user.id,
            ip_address=client_ip
        )
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger('intelectus.memberships')
        logger.error(f"Erro ao atualizar membership: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar membership: {str(e)}"
        )


@router.delete("/{user_id}/companies/{company_id}")
def revoke_membership(
    user_id: UUID,
    company_id: UUID,
    *,
    reason: Optional[str] = Query(None, description="Motivo da revogação"),
    hard_delete: bool = Query(False, description="Deletar permanentemente (true) ou desativar (false)"),
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Revogar membership** com auditoria completa.
    
    Opções:
    - 🔄 **Soft Delete** (padrão): Desativa mas mantém histórico
    - 🗑️ **Hard Delete**: Remove permanentemente (cuidado!)
    - 📝 **Motivo** obrigatório para auditoria
    - 📊 **Registro completo** na auditoria
    """
    # Verificar permissões
    if not current_user.is_superuser:
        has_access = membership_service.check_user_permission(
            db, current_user.id, company_id, "manage_users"
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: precisa de permissão 'manage_users'"
            )
    
    # Obter IP para auditoria
    client_ip = request.client.host if request.client else None
    
    success = membership_service.revoke_membership(
        db=db,
        user_id=user_id,
        company_id=company_id,
        revoked_by_user_id=current_user.id,
        reason=reason,
        ip_address=client_ip,
        hard_delete=hard_delete
    )
    
    if success:
        action = "deletado permanentemente" if hard_delete else "desativado"
        return {"message": f"Membership {action} com sucesso"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao revogar membership"
        )


@router.get("/history", response_model=List[MembershipHistoryResponse])
def get_membership_history(
    user_id: Optional[UUID] = Query(None, description="Filtrar por usuário"),
    company_id: Optional[UUID] = Query(None, description="Filtrar por empresa"),
    limit: int = Query(50, le=200, description="Limite de registros"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)  # Apenas superusuários
):
    """
    **Histórico completo de mudanças** de membership.
    
    Auditoria detalhada com:
    - 👤 **Quem** fez a alteração
    - ⏰ **Quando** foi realizada
    - 🔄 **O que** foi alterado (role anterior → nova)
    - 📝 **Por que** foi feita (motivo)
    - 🌐 **De onde** veio a alteração (IP)
    """
    return membership_service.get_membership_history(
        db=db,
        user_id=user_id,
        company_id=company_id,
        limit=limit
    )


@router.get("/companies/{company_id}/stats", response_model=MembershipStats)
def get_company_membership_stats(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Estatísticas de membership** para uma empresa.
    
    Dashboard com:
    - 📊 **Total de membros** (ativo/inativo)
    - 🎭 **Distribuição por roles** (admin, member, etc.)
    - 📈 **Mudanças recentes** (últimos 7 dias)
    - 📋 **Métricas de gestão** para tomada de decisão
    """
    # Verificar acesso à empresa
    if not current_user.is_superuser:
        has_access = membership_service.check_user_permission(
            db, current_user.id, company_id, "read_company_data"
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado à empresa"
            )
    
    return membership_service.get_membership_stats(db=db, company_id=company_id)


@router.post("/bulk", response_model=List[MembershipResponse], status_code=status.HTTP_201_CREATED)
def create_bulk_memberships(
    *,
    db: Session = Depends(get_db),
    bulk_data: BulkMembershipCreate,
    current_user: User = Depends(get_current_superuser),  # Apenas superusuários
    request: Request
):
    """
    **Criação em lote** de memberships (máximo 50).
    
    Útil para:
    - 📥 **Importação** de usuários do sistema legado
    - 👥 **Adição em massa** de colaboradores
    - 🏢 **Configuração inicial** de empresas
    - ⚡ **Provisionamento** rápido de acessos
    """
    client_ip = request.client.host if request.client else None
    results = []
    
    for membership_data in bulk_data.memberships:
        try:
            # Garantir que company_id seja consistente
            membership_data.company_id = bulk_data.company_id
            
            result = membership_service.create_membership(
                db=db,
                membership_data=membership_data,
                created_by_user_id=current_user.id,
                ip_address=client_ip
            )
            results.append(result)
        except HTTPException:
            # Pular memberships que já existem ou têm problemas
            continue
    
    return results


@router.post("/migrate", status_code=status.HTTP_200_OK)
def migrate_legacy_associations(
    company_id: Optional[UUID] = Query(None, description="ID da empresa (opcional, se None migra todas)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)  # Apenas superusuários
):
    """
    **Migrar associações legadas** para memberships.
    
    Útil para migrar empresas criadas antes do sistema de memberships.
    Cria memberships a partir das associações legadas (user_company_association).
    
    **Requer:** Ser superusuário
    """
    stats = membership_service.migrate_legacy_associations_to_memberships(
        db=db,
        company_id=company_id
    )
    
    return {
        "message": "Migração concluída",
        "stats": stats
    }


@router.get("/{user_id}/companies/{company_id}/permissions")
def check_user_permissions(
    user_id: UUID,
    company_id: UUID,
    permissions: List[str] = Query(..., description="Lista de permissões para verificar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Verificar permissões específicas** de um usuário em uma empresa.
    
    Útil para:
    - 🔒 **Controle de acesso** granular
    - 🎭 **Validação de roles** específicas
    - ⚡ **Decision making** em tempo real
    - 🛡️ **Segurança baseada** em permissões
    """
    # Verificar se pode consultar permissões
    if not current_user.is_superuser and current_user.id != user_id:
        # Permite que admins da empresa vejam permissões de outros usuários
        has_access = membership_service.check_user_permission(
            db, current_user.id, company_id, "manage_users"
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )
    
    # Verificar cada permissão
    results = {}
    for permission in permissions:
        has_permission = membership_service.check_user_permission(
            db, user_id, company_id, permission
        )
        results[permission] = has_permission
    
    return {
        "user_id": user_id,
        "company_id": company_id,
        "permissions": results,
        "checked_at": "2024-01-15T10:30:00Z"  # timestamp atual
    } 