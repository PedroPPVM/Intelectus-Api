from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.crud import company as crud_company
from app.services.access_control_service import access_control_service


class CompanyService:
    """
    Service para centralizar todas as regras de negócio de empresas.
    
    🎯 Objetivo: Eliminar transformações duplicadas, centralizar validações
    de CNPJ/CPF e padronizar relacionamentos User ↔ Company.
    
    Roadmap Fase 3.2 - Etapa 3 (Alta Prioridade)
    """
    
    def create_company_with_validation(
        self,
        db: Session,
        company_data: CompanyCreate,
        user: User
    ) -> Company:
        """
        Criar empresa com todas as validações de negócio.
        
        Centraliza lógica duplicada nos endpoints de criação.
        
        Args:
            db: Sessão do banco
            company_data: Dados da empresa
            user: Usuário executando a operação
            
        Returns:
            Company: Empresa criada
            
        Raises:
            HTTPException: Se validações falharem
        """
        # Validar regras de negócio
        self.validate_company_business_rules(company_data)
        
        # Validar documento único
        if not self.validate_unique_document(db, company_data.document):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este documento (CNPJ/CPF) já está cadastrado"
            )
        
        # Criar empresa
        company = crud_company.create(db, obj_in=company_data)
        
        return company
    
    def validate_unique_document(
        self,
        db: Session,
        document: str,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Validar se documento (CNPJ/CPF) é único no sistema.
        
        Centraliza validação duplicada em endpoints de criação/atualização.
        
        Args:
            db: Sessão do banco
            document: CNPJ ou CPF
            exclude_id: ID da empresa a excluir (para updates)
            
        Returns:
            bool: True se documento é único, False se já existe
        """
        existing_company = crud_company.get_by_document(db, document=document)
        
        # Se não encontrou, está disponível
        if not existing_company:
            return True
        
        # Se encontrou mas é a mesma empresa (update), está ok
        if exclude_id and existing_company.id == exclude_id:
            return True
        
        # Documento já em uso por outra empresa
        return False
    
    def transform_to_company_response(
        self, 
        company: Company
    ) -> CompanyResponse:
        """
        Transformar Company em CompanyResponse.
        
        Elimina transformação duplicada em +5 endpoints.
        Centraliza lógica de user_ids.
        
        Args:
            company: Empresa do banco
            
        Returns:
            CompanyResponse: Resposta formatada
        """
        company_data = CompanyResponse.model_validate(company)
        
        # Lógica de user_ids centralizada
        company_data.user_ids = [user.id for user in company.users]
        
        return company_data
    
    def transform_to_company_response_list(
        self,
        companies: List[Company]
    ) -> List[CompanyResponse]:
        """
        Transformar lista de empresas em CompanyResponse.
        
        Elimina loop de transformação duplicado nos endpoints.
        
        Args:
            companies: Lista de empresas do banco
            
        Returns:
            List[CompanyResponse]: Lista formatada
        """
        response_data = []
        
        for company in companies:
            company_data = self.transform_to_company_response(company)
            response_data.append(company_data)
        
        return response_data
    
    def get_user_companies_with_filters(
        self,
        db: Session,
        user: User,
        filters: Dict[str, Any]
    ) -> List[Company]:
        """
        Obter empresas do usuário com filtros.
        
        Centraliza lógica de acesso e filtros dos endpoints.
        
        Args:
            db: Sessão do banco
            user: Usuário fazendo a consulta
            filters: Dicionário com filtros (name, skip, limit)
            
        Returns:
            List[Company]: Empresas filtradas
        """
        # Extrair parâmetros
        skip = filters.get('skip', 0)
        limit = filters.get('limit', 100)
        name = filters.get('name')
        
        if user.is_superuser:
            # Superusuário pode ver todas as empresas
            if name:
                return crud_company.search_by_name(db, name=name, skip=skip, limit=limit)
            else:
                return crud_company.get_multi(db, skip=skip, limit=limit)
        else:
            # Usuário normal só vê suas empresas
            companies = crud_company.get_by_user(db, user_id=user.id)
            
            # Aplicar filtro de nome se fornecido
            if name:
                companies = [c for c in companies if name.lower() in c.name.lower()]
            
            # Aplicar paginação manual
            return companies[skip:skip + limit]
    
    def update_company_with_validation(
        self,
        db: Session,
        company_id: UUID,
        update_data: CompanyUpdate,
        user: User
    ) -> Company:
        """
        Atualizar empresa com validações completas.
        
        Centraliza lógica duplicada nos endpoints de update.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            update_data: Dados para atualização
            user: Usuário executando a operação
            
        Returns:
            Company: Empresa atualizada
        """
        # Validar acesso à empresa
        company = access_control_service.validate_company_access(
            db, user, company_id, "update_company_data"
        )
        
        # Validar regras de negócio se há mudanças relevantes
        if update_data.dict(exclude_unset=True):
            self.validate_company_business_rules(update_data)
        
        # Validar documento único se está sendo alterado
        if update_data.document and update_data.document != company.document:
            if not self.validate_unique_document(
                db, update_data.document, exclude_id=company_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este documento (CNPJ/CPF) já está cadastrado"
                )
        
        # Atualizar empresa
        updated_company = crud_company.update(db, db_obj=company, obj_in=update_data)
        
        return updated_company
    
    def can_delete_company(
        self,
        db: Session,
        company_id: UUID
    ) -> Tuple[bool, str]:
        """
        Verificar se empresa pode ser deletada.
        
        Centraliza validações de integridade referencial.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            
        Returns:
            Tuple[bool, str]: (pode_deletar, mensagem_erro)
        """
        company = crud_company.get(db, id=company_id)
        
        if not company:
            return False, "Empresa não encontrada"
        
        # Verificar se há processos associados
        if company.processes:
            count = len(company.processes)
            return False, f"Não é possível deletar empresa com {count} processo(s) associado(s)"
        
        # Verificar se há memberships ativos (via novo sistema)
        # TODO: Adicionar verificação via MembershipService quando necessário
        
        # Verificar se há alertas relacionados via processos
        # TODO: Adicionar verificação de alertas quando necessário
        
        return True, "Empresa pode ser deletada"
    
    def delete_company_with_validation(
        self,
        db: Session,
        company_id: UUID,
        user: User
    ) -> None:
        """
        Deletar empresa com validações completas.
        
        Centraliza lógica de exclusão com verificações de integridade.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            user: Usuário executando a operação (deve ser superusuário)
        """
        # Apenas superusuários podem deletar empresas
        access_control_service.validate_superuser(user)
        
        # Verificar se empresa existe
        company = crud_company.get(db, id=company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        
        # Verificar se pode deletar
        can_delete, error_message = self.can_delete_company(db, company_id)
        if not can_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Deletar empresa
        crud_company.delete(db, id=company_id)
    
    def get_company_full_stats(
        self,
        db: Session,
        company_id: UUID,
        user: User
    ) -> Dict[str, Any]:
        """
        Obter estatísticas completas da empresa.
        
        Centraliza lógica de dashboard empresarial.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            user: Usuário solicitando (deve ter acesso)
            
        Returns:
            Dict[str, Any]: Estatísticas completas
        """
        # Validar acesso
        company = access_control_service.validate_company_access(
            db, user, company_id, "view_reports"
        )
        
        # Estatísticas básicas da empresa
        stats = {
            "company_id": str(company_id),
            "company_name": company.name,
            "company_document": company.document,
            "total_users": len(company.users),
            "total_processes": len(company.processes),
            "user_ids": [str(user.id) for user in company.users],
            "requested_by_user_id": str(user.id),
            "is_superuser_request": user.is_superuser
        }
        
        # Estatísticas detalhadas de processos (se houver)
        if company.processes:
            from app.models.process import ProcessType, ProcessStatus
            
            # Por tipo
            type_stats = {}
            for process_type in ProcessType:
                count = len([p for p in company.processes if p.process_type == process_type])
                type_stats[process_type.value] = count
            
            # Por status
            status_stats = {}
            for process_status in ProcessStatus:
                count = len([p for p in company.processes if p.status == process_status])
                status_stats[process_status.value] = count
            
            stats["processes_by_type"] = type_stats
            stats["processes_by_status"] = status_stats
        
        return stats
    
    def validate_company_business_rules(
        self, 
        company_data: CompanyCreate | CompanyUpdate
    ) -> None:
        """
        Validar regras de negócio específicas de empresas.
        
        Centraliza validações que podem estar espalhadas.
        
        Args:
            company_data: Dados da empresa para validar
            
        Raises:
            HTTPException: Se alguma regra for violada
        """
        # Validação de nome
        if hasattr(company_data, 'name') and company_data.name:
            name = company_data.name.strip()
            
            if len(name) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nome da empresa deve ter pelo menos 2 caracteres"
                )
            
            if len(name) > 255:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nome da empresa deve ter no máximo 255 caracteres"
                )
        
        # Validação de documento (CNPJ/CPF)
        if hasattr(company_data, 'document') and company_data.document:
            document = company_data.document.strip().replace('.', '').replace('/', '').replace('-', '')
            
            if len(document) not in [11, 14]:  # CPF: 11 dígitos, CNPJ: 14 dígitos
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Documento deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ)"
                )
            
            if not document.isdigit():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Documento deve conter apenas números"
                )
        
        # Validação de email se fornecido
        if hasattr(company_data, 'email') and company_data.email:
            email = company_data.email.strip()
            
            if '@' not in email or '.' not in email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email deve ter formato válido"
                )
            
            if len(email) > 255:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email deve ter no máximo 255 caracteres"
                )
        
        # Validação de telefone se fornecido
        if hasattr(company_data, 'phone') and company_data.phone:
            phone = company_data.phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            if len(phone) < 10 or len(phone) > 15:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Telefone deve ter entre 10 e 15 dígitos"
                )
    
    def get_company_with_access_validation(
        self,
        db: Session,
        company_id: UUID,
        user: User,
        required_permission: str = "read_company_data"
    ) -> Company:
        """
        Obter empresa com validação de acesso.
        
        Wrapper conveniente que combina busca + validação.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            user: Usuário fazendo a consulta
            required_permission: Permissão necessária
            
        Returns:
            Company: Empresa se acesso válido
            
        Raises:
            HTTPException: Se não encontrada ou sem acesso
        """
        return access_control_service.validate_company_access(
            db, user, company_id, required_permission
        )
    
    def search_companies_by_name(
        self,
        db: Session,
        user: User,
        name: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Company]:
        """
        Buscar empresas por nome com controle de acesso.
        
        Centraliza lógica de busca respeitando permissões do usuário.
        
        Args:
            db: Sessão do banco
            user: Usuário fazendo a busca
            name: Nome para buscar
            skip: Registros para pular
            limit: Máximo de registros
            
        Returns:
            List[Company]: Empresas encontradas
        """
        if user.is_superuser:
            return crud_company.search_by_name(db, name=name, skip=skip, limit=limit)
        else:
            # Usuário normal só busca em suas empresas
            user_companies = crud_company.get_by_user(db, user_id=user.id)
            
            # Filtrar por nome
            filtered = [c for c in user_companies if name.lower() in c.name.lower()]
            
            # Aplicar paginação
            return filtered[skip:skip + limit]


# Instância global para uso nos endpoints
company_service = CompanyService() 