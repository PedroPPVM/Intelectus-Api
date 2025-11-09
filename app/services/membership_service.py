from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.models.user import User
from app.models.company import Company
from app.models.membership import (
    UserCompanyMembership, MembershipHistory, UserCompanyPermission,
    MembershipRole, MembershipPermission
)
from app.schemas.membership import (
    MembershipCreate, MembershipUpdate, MembershipResponse, 
    MembershipHistoryResponse, MembershipStats, MembershipSummary
)


class MembershipService:
    """
    Service robusto para gerenciar relacionamentos User ↔ Company.
    
    Responsabilidades:
    - Criar/atualizar/deletar memberships
    - Gerenciar permissões granulares
    - Manter auditoria completa
    - Validar regras de negócio
    - Fornecer consultas otimizadas
    """
    
    def create_membership(
        self,
        db: Session,
        *,
        membership_data: MembershipCreate,
        created_by_user_id: UUID,
        ip_address: Optional[str] = None
    ) -> MembershipResponse:
        """
        Criar novo membership com auditoria completa.
        """
        # Validações básicas
        self._validate_user_and_company(db, membership_data.user_id, membership_data.company_id)
        
        # Verificar se membership já existe
        existing = db.query(UserCompanyMembership).filter(
            and_(
                UserCompanyMembership.user_id == membership_data.user_id,
                UserCompanyMembership.company_id == membership_data.company_id
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Membership já existe para este usuário e empresa"
            )
        
        # Criar membership principal
        membership = UserCompanyMembership(
            user_id=membership_data.user_id,
            company_id=membership_data.company_id,
            role=MembershipRole(membership_data.role.value),
            is_active=True,
            created_by_user_id=created_by_user_id
        )
        
        db.add(membership)
        db.flush()  # Para obter as chaves
        
        # Adicionar permissões específicas se fornecidas
        if membership_data.permissions:
            for perm in membership_data.permissions:
                permission = UserCompanyPermission(
                    user_id=membership_data.user_id,
                    company_id=membership_data.company_id,
                    permission=MembershipPermission(perm.value),
                    granted_by_user_id=created_by_user_id
                )
                db.add(permission)
        
        # Criar registro de auditoria
        history = MembershipHistory(
            user_id=membership_data.user_id,
            company_id=membership_data.company_id,
            action="CREATE",
            new_role=MembershipRole(membership_data.role.value),
            reason=membership_data.reason,
            performed_by_user_id=created_by_user_id,
            ip_address=ip_address
        )
        db.add(history)
        
        # Atualizar tabela legacy para compatibilidade
        self._sync_legacy_association(db, membership_data.user_id, membership_data.company_id, "ADD")
        
        db.commit()
        db.refresh(membership)
        
        return self._build_membership_response(db, membership)
    
    def update_membership(
        self,
        db: Session,
        *,
        user_id: UUID,
        company_id: UUID,
        membership_update: MembershipUpdate,
        updated_by_user_id: UUID,
        ip_address: Optional[str] = None
    ) -> MembershipResponse:
        """
        Atualizar membership existente com auditoria.
        """
        # Buscar membership existente
        membership = db.query(UserCompanyMembership).filter(
            and_(
                UserCompanyMembership.user_id == user_id,
                UserCompanyMembership.company_id == company_id
            )
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership não encontrado"
            )
        
        # Guardar valores antigos para auditoria
        old_role = membership.role
        old_is_active = membership.is_active
        
        # Aplicar mudanças
        changes = []
        if membership_update.role and membership_update.role.value != membership.role.value:
            membership.role = MembershipRole(membership_update.role.value)
            changes.append(f"role: {old_role.value} → {membership.role.value}")
        
        if membership_update.is_active is not None and membership_update.is_active != membership.is_active:
            membership.is_active = membership_update.is_active
            changes.append(f"is_active: {old_is_active} → {membership.is_active}")
        
        # Atualizar permissões se fornecidas
        if membership_update.permissions is not None:
            # Remover permissões existentes
            db.query(UserCompanyPermission).filter(
                and_(
                    UserCompanyPermission.user_id == user_id,
                    UserCompanyPermission.company_id == company_id
                )
            ).delete()
            
            # Adicionar novas permissões
            for perm in membership_update.permissions:
                permission = UserCompanyPermission(
                    user_id=user_id,
                    company_id=company_id,
                    permission=MembershipPermission(perm.value),
                    granted_by_user_id=updated_by_user_id
                )
                db.add(permission)
            
            changes.append(f"permissions: {len(membership_update.permissions)} updated")
        
        membership.updated_at = func.now()
        
        # Criar registro de auditoria se houve mudanças
        if changes:
            history = MembershipHistory(
                user_id=user_id,
                company_id=company_id,
                action="UPDATE",
                old_role=old_role,
                new_role=membership.role,
                reason=membership_update.reason or f"Atualizado: {', '.join(changes)}",
                performed_by_user_id=updated_by_user_id,
                ip_address=ip_address
            )
            db.add(history)
        
        db.commit()
        db.refresh(membership)
        
        return self._build_membership_response(db, membership)
    
    def revoke_membership(
        self,
        db: Session,
        *,
        user_id: UUID,
        company_id: UUID,
        revoked_by_user_id: UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        hard_delete: bool = False
    ) -> bool:
        """
        Revogar membership (soft delete ou hard delete).
        """
        membership = db.query(UserCompanyMembership).filter(
            and_(
                UserCompanyMembership.user_id == user_id,
                UserCompanyMembership.company_id == company_id
            )
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership não encontrado"
            )
        
        if hard_delete:
            # Deletar permissões associadas
            db.query(UserCompanyPermission).filter(
                and_(
                    UserCompanyPermission.user_id == user_id,
                    UserCompanyPermission.company_id == company_id
                )
            ).delete()
            
            # Deletar membership
            db.delete(membership)
            action = "DELETE"
        else:
            # Desativar membership (soft delete)
            membership.is_active = False
            membership.updated_at = func.now()
            action = "DEACTIVATE"
        
        # Criar registro de auditoria
        history = MembershipHistory(
            user_id=user_id,
            company_id=company_id,
            action=action,
            old_role=membership.role,
            reason=reason or f"Membership {'deletado' if hard_delete else 'desativado'}",
            performed_by_user_id=revoked_by_user_id,
            ip_address=ip_address
        )
        db.add(history)
        
        # Remover da tabela legacy
        if hard_delete:
            self._sync_legacy_association(db, user_id, company_id, "REMOVE")
        
        db.commit()
        return True
    
    def get_user_companies(
        self,
        db: Session,
        user_id: UUID,
        include_permissions: bool = False,
        active_only: bool = True
    ) -> List[MembershipResponse]:
        """
        Buscar empresas de um usuário com informações de membership.
        """
        query = db.query(UserCompanyMembership).filter(
            UserCompanyMembership.user_id == user_id
        )
        
        if active_only:
            query = query.filter(UserCompanyMembership.is_active == True)
        
        memberships = query.all()
        
        return [self._build_membership_response(db, m, include_permissions) for m in memberships]
    
    def get_company_members(
        self,
        db: Session,
        company_id: UUID,
        role_filter: Optional[str] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[MembershipSummary]:
        """
        Buscar membros de uma empresa com paginação.
        """
        query = db.query(UserCompanyMembership).filter(
            UserCompanyMembership.company_id == company_id
        )
        
        if active_only:
            query = query.filter(UserCompanyMembership.is_active == True)
        
        if role_filter:
            query = query.filter(UserCompanyMembership.role == MembershipRole(role_filter))
        
        memberships = query.offset(skip).limit(limit).all()
        
        # OTIMIZADO: Usar batch loading para evitar N+1 queries
        # Carregar usuários e empresas em lotes
        if not memberships:
            return []
        
        user_ids = list(set([m.user_id for m in memberships]))
        company_ids = list(set([m.company_id for m in memberships]))
        
        # Buscar usuários e empresas em lotes
        users_dict = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
        companies_dict = {c.id: c for c in db.query(Company).filter(Company.id.in_(company_ids)).all()}
        
        # Contar permissões em lote para todos os memberships
        permission_counts = {}
        if memberships:
            # Criar lista de tuplas (user_id, company_id) para filtrar
            membership_keys = [(m.user_id, m.company_id) for m in memberships]
            
            # Buscar todas as permissões relevantes
            all_permissions = db.query(UserCompanyPermission).filter(
                and_(
                    UserCompanyPermission.user_id.in_(user_ids),
                    UserCompanyPermission.company_id.in_(company_ids)
                )
            ).all()
            
            # Contar permissões por membership
            for perm in all_permissions:
                key = (perm.user_id, perm.company_id)
                if key in membership_keys:
                    permission_counts[key] = permission_counts.get(key, 0) + 1
        
        # Converter para summary com informações de usuário
        summaries = []
        for membership in memberships:
            user = users_dict.get(membership.user_id)
            company = companies_dict.get(membership.company_id)
            
            # Obter contagem de permissões do dicionário
            permissions_count = permission_counts.get(
                (membership.user_id, membership.company_id), 0
            )
            
            summary = MembershipSummary(
                user_id=membership.user_id,
                company_id=membership.company_id,
                role=membership.role.value,
                is_active=membership.is_active,
                permissions_count=permissions_count,
                user_name=user.full_name if user else None,
                user_email=user.email if user else None,
                company_name=company.name if company else None,
                created_at=membership.created_at
            )
            summaries.append(summary)
        
        return summaries
    
    def get_membership_history(
        self,
        db: Session,
        user_id: Optional[UUID] = None,
        company_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[MembershipHistoryResponse]:
        """
        Buscar histórico de mudanças de membership.
        """
        query = db.query(MembershipHistory)
        
        if user_id:
            query = query.filter(MembershipHistory.user_id == user_id)
        if company_id:
            query = query.filter(MembershipHistory.company_id == company_id)
        
        history = query.order_by(desc(MembershipHistory.performed_at)).limit(limit).all()
        
        # Enriquecer com dados de usuário e empresa
        responses = []
        for h in history:
            user = db.query(User).filter(User.id == h.user_id).first()
            company = db.query(Company).filter(Company.id == h.company_id).first()
            performed_by = db.query(User).filter(User.id == h.performed_by_user_id).first()
            
            response = MembershipHistoryResponse(
                id=h.id,
                user_id=h.user_id,
                company_id=h.company_id,
                action=h.action,
                old_role=h.old_role.value if h.old_role else None,
                new_role=h.new_role.value if h.new_role else None,
                reason=h.reason,
                performed_by_user_id=h.performed_by_user_id,
                performed_at=h.performed_at,
                ip_address=h.ip_address,
                user_name=user.full_name if user else None,
                company_name=company.name if company else None,
                performed_by_name=performed_by.full_name if performed_by else None
            )
            responses.append(response)
        
        return responses
    
    def get_membership_stats(
        self,
        db: Session,
        company_id: UUID
    ) -> MembershipStats:
        """
        Obter estatísticas de membership para uma empresa.
        """
        # Contagens básicas
        total_query = db.query(UserCompanyMembership).filter(
            UserCompanyMembership.company_id == company_id
        )
        
        total_members = total_query.count()
        active_members = total_query.filter(UserCompanyMembership.is_active == True).count()
        inactive_members = total_members - active_members
        
        # Contagem por role
        roles_query = db.query(
            UserCompanyMembership.role,
            func.count(UserCompanyMembership.role).label('count')
        ).filter(
            and_(
                UserCompanyMembership.company_id == company_id,
                UserCompanyMembership.is_active == True
            )
        ).group_by(UserCompanyMembership.role).all()
        
        members_by_role = {role.value: count for role, count in roles_query}
        
        # Mudanças recentes (últimos 7 dias)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_changes = db.query(MembershipHistory).filter(
            and_(
                MembershipHistory.company_id == company_id,
                MembershipHistory.performed_at >= seven_days_ago
            )
        ).count()
        
        return MembershipStats(
            company_id=company_id,
            total_members=total_members,
            active_members=active_members,
            inactive_members=inactive_members,
            members_by_role=members_by_role,
            recent_changes=recent_changes
        )
    
    def check_user_permission(
        self,
        db: Session,
        user_id: UUID,
        company_id: UUID,
        permission: str
    ) -> bool:
        """
        Verificar se usuário tem permissão específica em uma empresa.
        """
        # Verificar se membership está ativo
        membership = db.query(UserCompanyMembership).filter(
            and_(
                UserCompanyMembership.user_id == user_id,
                UserCompanyMembership.company_id == company_id,
                UserCompanyMembership.is_active == True
            )
        ).first()
        
        if not membership:
            return False
        
        # OWNERs e ADMINs têm todas as permissões
        if membership.role in [MembershipRole.OWNER, MembershipRole.ADMIN]:
            return True
        
        # Verificar permissão específica
        specific_permission = db.query(UserCompanyPermission).filter(
            and_(
                UserCompanyPermission.user_id == user_id,
                UserCompanyPermission.company_id == company_id,
                UserCompanyPermission.permission == MembershipPermission(permission),
                or_(
                    UserCompanyPermission.expires_at.is_(None),
                    UserCompanyPermission.expires_at > func.now()
                )
            )
        ).first()
        
        return specific_permission is not None
    
    def _validate_user_and_company(self, db: Session, user_id: UUID, company_id: UUID):
        """Validar se usuário e empresa existem."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
    
    def _build_membership_response(
        self,
        db: Session,
        membership: UserCompanyMembership,
        include_permissions: bool = True
    ) -> MembershipResponse:
        """Construir resposta completa de membership."""
        # Buscar dados do usuário e empresa
        user = db.query(User).filter(User.id == membership.user_id).first()
        company = db.query(Company).filter(Company.id == membership.company_id).first()
        
        # Buscar permissões se solicitado
        permissions = []
        if include_permissions:
            perms = db.query(UserCompanyPermission).filter(
                and_(
                    UserCompanyPermission.user_id == membership.user_id,
                    UserCompanyPermission.company_id == membership.company_id
                )
            ).all()
            
            permissions = [
                {
                    "permission": p.permission.value,
                    "granted_at": p.granted_at,
                    "granted_by_user_id": p.granted_by_user_id,
                    "expires_at": p.expires_at
                }
                for p in perms
            ]
        
        return MembershipResponse(
            user_id=membership.user_id,
            company_id=membership.company_id,
            role=membership.role.value,
            is_active=membership.is_active,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
            created_by_user_id=membership.created_by_user_id,
            permissions=permissions,
            user_name=user.full_name if user else None,
            user_email=user.email if user else None,
            company_name=company.name if company else None
        )
    
    def _sync_legacy_association(
        self,
        db: Session,
        user_id: UUID,
        company_id: UUID,
        action: str
    ):
        """
        Sincronizar com tabela legacy user_company_association para compatibilidade.
        """
        from app.models.user import user_company_association
        
        if action == "ADD":
            # Verificar se já existe na tabela legacy
            existing = db.execute(
                user_company_association.select().where(
                    and_(
                        user_company_association.c.user_id == user_id,
                        user_company_association.c.company_id == company_id
                    )
                )
            ).first()
            
            if not existing:
                db.execute(
                    user_company_association.insert().values(
                        user_id=user_id,
                        company_id=company_id
                    )
                )
        
        elif action == "REMOVE":
            db.execute(
                user_company_association.delete().where(
                    and_(
                        user_company_association.c.user_id == user_id,
                        user_company_association.c.company_id == company_id
                    )
                )
            )


# Instância singleton do service
membership_service = MembershipService() 