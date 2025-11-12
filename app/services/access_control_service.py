from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.company import Company
from app.models.process import Process
from app.models.alert import Alert
from app.crud import company as crud_company, process as crud_process, alert as crud_alert
from app.services.membership_service import membership_service


class AccessControlService:
    """
    Service para centraliazar todas as validações de acesso do sistema.
    
    🎯 Objetivo: Eliminar +50 linhas de código duplicado nos endpoints
    e centralizar todas as regras de autorização em um único ponto.
    
    Roadmap Fase 3.2 - Etapa 1 (Prioridade Máxima)
    """
    
    def validate_superuser(self, user: User) -> None:
        """
        Validar se usuário é superusuário.
        
        Centraliza validação que está duplicada em vários endpoints.
        """
        if not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: apenas administradores têm acesso"
            )
    
    def validate_company_access(
        self, 
        db: Session, 
        user: User, 
        company_id: UUID,
        required_permission: str = "read_company_data"
    ) -> Company:
        """
        Validar se usuário tem acesso à empresa especificada.
        
        Centraliza lógica duplicada em +10 endpoints.
        Usa MembershipService para validação granular de permissões.
        
        Returns:
            Company: A empresa se acesso válido
            
        Raises:
            HTTPException: 404 se empresa não existe, 403 se sem permissão
        """
        # Superusuários têm acesso total
        if user.is_superuser:
            company = crud_company.get(db, id=company_id)
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Empresa não encontrada"
                )
            return company
        
        # Verificar se empresa existe
        company = crud_company.get(db, id=company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        
        # Usar MembershipService para validação granular
        has_permission = membership_service.check_user_permission(
            db, user.id, company_id, required_permission
        )
        
        if not has_permission:
            # Fallback para sistema legado (user_company_association)
            if user not in company.users:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Acesso negado: você precisa ter permissão '{required_permission}' na empresa"
                )
        
        return company
    
    def validate_process_access(
        self, 
        db: Session, 
        user: User, 
        process_id: UUID,
        required_permission: str = "read_processes"
    ) -> Process:
        """
        Validar se usuário tem acesso ao processo especificado.
        
        Centraliza lógica de validação que está duplicada em +8 endpoints.
        
        Returns:
            Process: O processo se acesso válido
            
        Raises:
            HTTPException: 404 se processo não existe, 403 se sem permissão
        """
        # Buscar processo
        process = crud_process.get(db, id=process_id)
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processo não encontrado"
            )
        
        # Superusuários têm acesso total
        if user.is_superuser:
            return process
        
        # Validar acesso via empresa do processo
        try:
            self.validate_company_access(db, user, process.company_id, required_permission)
            return process
        except HTTPException as e:
            # Converter erro de empresa para contexto de processo
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado ao processo"
                )
            raise
    
    def validate_process_in_company(
        self,
        db: Session,
        process_id: UUID,
        company_id: UUID
    ) -> Process:
        """
        Validar que processo pertence à empresa especificada.
        
        Usado nos endpoints company-oriented para garantir isolamento.
        
        Returns:
            Process: O processo se pertence à empresa
            
        Raises:
            HTTPException: 404 se não encontrado ou não pertence à empresa
        """
        process = crud_process.get(db, id=process_id)
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processo não encontrado"
            )
        
        if process.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processo não encontrado nesta empresa"
            )
        
        return process
    
    def validate_alert_access(
        self, 
        db: Session, 
        user: User, 
        alert_id: UUID
    ) -> Alert:
        """
        Validar se usuário tem acesso ao alerta especificado.
        
        Centraliza lógica duplicada nos endpoints de alertas.
        
        Returns:
            Alert: O alerta se acesso válido
            
        Raises:
            HTTPException: 404 se alerta não existe, 403 se sem permissão  
        """
        alert = crud_alert.get(db, id=alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alerta não encontrado"
            )
        
        # Superusuários têm acesso total
        if user.is_superuser:
            return alert
        
        # Usuários só podem acessar seus próprios alertas
        if alert.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )
        
        return alert
    
    def check_user_company_relationship(
        self, 
        db: Session, 
        user: User, 
        company_id: UUID
    ) -> bool:
        """
        Verificar se usuário tem relacionamento com empresa.
        
        Combina validação via MembershipService + sistema legado.
        
        Returns:
            bool: True se usuário tem acesso à empresa
        """
        if user.is_superuser:
            return True
        
        # Verificar via MembershipService (sistema novo)
        has_membership = membership_service.check_user_permission(
            db, user.id, company_id, "read_company_data"
        )
        
        if has_membership:
            return True
        
        # Fallback para sistema legado
        company = crud_company.get(db, id=company_id)
        if company and user in company.users:
            return True
        
        return False
    
    def get_user_accessible_companies(
        self, 
        db: Session, 
        user: User
    ) -> List[Company]:
        """
        Obter todas as empresas acessíveis ao usuário.
        
        Otimiza consultas que são repetidas nos endpoints.
        
        Returns:
            List[Company]: Lista de empresas com acesso
        """
        if user.is_superuser:
            return crud_company.get_multi(db, skip=0, limit=1000)
        
        # Usar CRUD otimizado
        return crud_company.get_by_user(db, user_id=user.id)
    
    def get_user_accessible_processes(
        self, 
        db: Session, 
        user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[Process]:
        """
        Obter todos os processos acessíveis ao usuário.
        
        Centraliza lógica de filtragem de processos por usuário.
        
        Returns:
            List[Process]: Lista de processos com acesso
        """
        if user.is_superuser:
            return crud_process.get_multi(db, skip=skip, limit=limit)
        
        # Usar CRUD otimizado
        return crud_process.get_by_user_companies(
            db, user_id=user.id, skip=skip, limit=limit
        )
    
    def validate_company_process_creation_access(
        self,
        db: Session,
        user: User,
        company_id: UUID
    ) -> Company:
        """
        Validar acesso para criar processo em empresa específica.
        
        Valida tanto acesso à empresa quanto permissão de criação.
        
        Returns:
            Company: A empresa se usuário pode criar processos
        """
        return self.validate_company_access(
            db, user, company_id, "create_processes"
        )
    
    def validate_company_process_update_access(
        self,
        db: Session,
        user: User,
        company_id: UUID,
        process_id: UUID
    ) -> tuple[Company, Process]:
        """
        Validar acesso para atualizar processo específico.
        
        Valida empresa, processo e permissão de atualização.
        
        Returns:
            tuple[Company, Process]: Empresa e processo se acesso válido
        """
        # Validar acesso à empresa
        company = self.validate_company_access(
            db, user, company_id, "update_processes"
        )
        
        # Validar que processo pertence à empresa
        process = self.validate_process_in_company(
            db, process_id, company_id
        )
        
        return company, process
    
    def validate_company_process_delete_access(
        self,
        db: Session,
        user: User,
        company_id: UUID,
        process_id: UUID
    ) -> tuple[Company, Process]:
        """
        Validar acesso para deletar processo específico.
        
        Valida empresa, processo e permissão de exclusão.
        
        Returns:
            tuple[Company, Process]: Empresa e processo se acesso válido
        """
        # Validar acesso à empresa  
        company = self.validate_company_access(
            db, user, company_id, "delete_processes"
        )
        
        # Validar que processo pertence à empresa
        process = self.validate_process_in_company(
            db, process_id, company_id
        )
        
        return company, process


# Instância global para uso nos endpoints
access_control_service = AccessControlService() 