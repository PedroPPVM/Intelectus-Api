from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.process import Process, ProcessType
from app.models.user import User
from app.schemas.process import ProcessCreate, ProcessUpdate, ProcessSummary
from app.crud import process as crud_process
from app.services.access_control_service import access_control_service


class ProcessService:
    """
    Service para centralizar todas as regras de negócio de processos.
    
    🎯 Objetivo: Eliminar transformações duplicadas e centralizar
    lógicas complexas de processos em um único local testável.
    
    Roadmap Fase 3.2 - Etapa 2 (Alta Prioridade)
    """
    
    def create_process_with_validation(
        self,
        db: Session,
        process_data: ProcessCreate,
        company_id: UUID,
        user: User
    ) -> Process:
        """
        Criar processo com todas as validações de negócio.
        
        Centraliza lógica que está duplicada nos endpoints de criação.
        
        Args:
            db: Sessão do banco
            process_data: Dados do processo
            company_id: ID da empresa (forçado por segurança)
            user: Usuário executando a operação
            
        Returns:
            Process: Processo criado
            
        Raises:
            HTTPException: Se validações falharem
        """
        # Validar acesso à empresa
        company = access_control_service.validate_company_access(
            db, user, company_id, "create_processes"
        )
        
        # Forçar company_id por segurança (evita manipulação de dados)
        process_data.company_id = company_id
        
        # Validar regras de negócio
        self.validate_process_business_rules(process_data)
        
        # Validar número único na empresa
        if not self.validate_unique_process_number(
            db, process_data.process_number, company_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este número de processo já está cadastrado nesta empresa"
            )
        
        # Criar processo
        process = crud_process.create(db, obj_in=process_data)
        
        return process
    
    def validate_unique_process_number(
        self,
        db: Session,
        process_number: str,
        company_id: UUID,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Validar se número do processo é único na empresa.
        
        Centraliza validação duplicada em endpoints de criação/atualização.
        
        Args:
            db: Sessão do banco
            process_number: Número do processo
            company_id: ID da empresa
            exclude_id: ID do processo a excluir (para updates)
            
        Returns:
            bool: True se número é único, False se já existe
        """
        existing_process = crud_process.get_by_company_and_number(
            db, company_id=company_id, process_number=process_number
        )
        
        # Se não encontrou, está disponível
        if not existing_process:
            return True
        
        # Se encontrou mas é o mesmo processo (update), está ok
        if exclude_id and existing_process.id == exclude_id:
            return True
        
        # Número já em uso por outro processo
        return False
    
    def transform_to_process_summary(self, processes: List[Process]) -> List[ProcessSummary]:
        """
        Transformar lista de Process em ProcessSummary para listagens.
        Atualizado para o modelo Process remodelado.
        
        Centraliza lógica de transformação que estava duplicada em vários endpoints.
        
        Args:
            processes: Lista de processos do banco
            
        Returns:
            List[ProcessSummary]: Lista de processos resumidos
        """
        summaries = []
        
        for process in processes:
            # Usar title diretamente (não temos mais short_title)
            display_title = process.title
            
            # Se título muito longo, truncar para exibição
            if display_title and len(display_title) > 100:
                display_title = display_title[:97] + "..."
            
            summary = ProcessSummary(
                id=process.id,
                process_number=process.process_number,
                title=display_title or "TÍTULO NÃO INFORMADO",
                process_type=process.process_type,
                status=process.status,
                depositor=process.depositor,
                company_id=process.company_id,
                created_at=process.created_at,
                attorney=process.attorney,
                cnpj_depositor=process.cnpj_depositor,
                cpf_depositor=process.cpf_depositor,
                deposit_date=process.deposit_date,
                concession_date=process.concession_date,
                validity_date=process.validity_date,
                situation=process.situation
            )
            
            summaries.append(summary)
        
        return summaries
    
    def get_company_processes_with_filters(
        self,
        db: Session,
        company_id: UUID,
        user: User,
        filters: Dict[str, Any]
    ) -> List[Process]:
        """
        Obter processos da empresa com filtros otimizados.
        
        Centraliza lógica de filtros que está nos endpoints.
        Usa índices otimizados automaticamente.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            user: Usuário fazendo a consulta
            filters: Dicionário com filtros (type, status, title, order_by, etc.)
            
        Returns:
            List[Process]: Processos filtrados
        """
        # Validar acesso à empresa
        access_control_service.validate_company_access(
            db, user, company_id, "read_processes"
        )
        
        # Extrair parâmetros com defaults
        skip = filters.get('skip', 0)
        limit = filters.get('limit', 100)
        process_type = filters.get('process_type')
        status_filter = filters.get('status')
        title = filters.get('title')
        order_by = filters.get('order_by', 'created_at')
        order_desc = filters.get('order_desc', True)
        
        # Aplicar filtros usando índices otimizados
        if process_type:
            # USA ÍNDICE: ix_process_company_type
            return crud_process.get_by_company_and_type(
                db, company_id=company_id, process_type=process_type, 
                skip=skip, limit=limit
            )
        elif status_filter:
            # USA ÍNDICE: ix_process_company_status
            return crud_process.get_by_company_and_status(
                db, company_id=company_id, status=status_filter, 
                skip=skip, limit=limit
            )
        elif title:
            # USA ÍNDICE: ix_process_company_title_search
            return crud_process.search_by_company_and_title(
                db, company_id=company_id, title=title, 
                skip=skip, limit=limit
            )
        else:
            # USA ÍNDICE: ix_process_company_created OU ix_process_company_updated
            return crud_process.get_by_company_optimized(
                db, company_id=company_id, skip=skip, limit=limit,
                order_by=order_by, order_desc=order_desc
            )
    
    def update_process_with_validation(
        self,
        db: Session,
        process_id: UUID,
        update_data: ProcessUpdate,
        company_id: UUID,
        user: User
    ) -> Process:
        """
        Atualizar processo com validações completas.
        
        Centraliza lógica duplicada nos endpoints de update.
        
        Args:
            db: Sessão do banco
            process_id: ID do processo
            update_data: Dados para atualização
            company_id: ID da empresa (company-oriented)
            user: Usuário executando a operação
            
        Returns:
            Process: Processo atualizado
        """
        # Validar acesso completo (empresa + processo + permissão)
        company, process = access_control_service.validate_company_process_update_access(
            db, user, company_id, process_id
        )
        
        # Validar regras de negócio se há mudanças relevantes
        if update_data.dict(exclude_unset=True):
            self.validate_process_business_rules(update_data)
        
        # Validar número único se está sendo alterado
        if (update_data.process_number and 
            update_data.process_number != process.process_number):
            
            if not self.validate_unique_process_number(
                db, update_data.process_number, company_id, exclude_id=process_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este número de processo já está cadastrado nesta empresa"
                )
        
        # Atualizar processo
        updated_process = crud_process.update(db, db_obj=process, obj_in=update_data)
        
        return updated_process
    
    def mark_process_scraped_with_audit(
        self,
        db: Session,
        process_id: UUID,
        user: User
    ) -> Process:
        """
        Marcar processo como recém-scrapado com auditoria.
        
        Usado pelo sistema de scraping para tracking.
        
        Args:
            db: Sessão do banco
            process_id: ID do processo
            user: Usuário/sistema executando (deve ser superusuário)
            
        Returns:
            Process: Processo com timestamp atualizado
        """
        # Apenas superusuários (sistema de scraping)
        access_control_service.validate_superuser(user)
        
        # Atualizar timestamp
        updated_process = crud_process.update_scraped_at(db, id=process_id)
        
        if not updated_process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processo não encontrado"
            )
        
        return updated_process
    
    def validate_process_business_rules(
        self,
        process_data: ProcessCreate | ProcessUpdate
    ) -> bool:
        """
        Validar regras de negócio dos processos.
        Atualizado para o modelo Process remodelado.
        
        Centraliza validações que estavam duplicadas nos endpoints.
        
        Args:
            process_data: Dados do processo para validar
            
        Returns:
            bool: True se validações passaram
            
        Raises:
            HTTPException: Se alguma validação falhar
        """
        # Validação de título obrigatório
        if hasattr(process_data, 'title') and process_data.title:
            title = process_data.title.strip()
            
            if len(title) < 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Título deve ter pelo menos 5 caracteres"
                )
            
            if len(title) > 1000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Título não pode exceder 1000 caracteres"
                )
        
        # Validação de CNPJ se fornecido
        if hasattr(process_data, 'cnpj_depositor') and process_data.cnpj_depositor:
            cnpj = process_data.cnpj_depositor.strip()
            # Validação básica de CNPJ (14 dígitos)
            digits_only = ''.join(filter(str.isdigit, cnpj))
            if len(digits_only) != 14:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CNPJ deve conter exatamente 14 dígitos"
                )
        
        # Validação de CPF se fornecido
        if hasattr(process_data, 'cpf_depositor') and process_data.cpf_depositor:
            cpf = process_data.cpf_depositor.strip()
            # Validação básica de CPF (11 dígitos)
            digits_only = ''.join(filter(str.isdigit, cpf))
            if len(digits_only) != 11:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CPF deve conter exatamente 11 dígitos"
                )
        
        # Validação de datas lógicas
        if (hasattr(process_data, 'deposit_date') and hasattr(process_data, 'concession_date') and
            process_data.deposit_date and process_data.concession_date):
            if process_data.deposit_date > process_data.concession_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data de depósito não pode ser posterior à data de concessão"
                )
        
        # Validação de depositante obrigatório
        if (hasattr(process_data, 'depositor') and 
            hasattr(process_data, 'cnpj_depositor') and 
            hasattr(process_data, 'cpf_depositor')):
            
            if (not process_data.depositor and 
                not process_data.cnpj_depositor and 
                not process_data.cpf_depositor):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="É necessário informar pelo menos nome do depositante, CNPJ ou CPF"
                )
        
        return True
    
    def get_process_statistics_summary(
        self,
        db: Session,
        company_id: UUID,
        user: User
    ) -> Dict[str, Any]:
        """
        Obter estatísticas completas dos processos da empresa.
        
        Centraliza lógica do endpoint de estatísticas usando índices otimizados.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            user: Usuário solicitando (deve ter permissão de relatórios)
            
        Returns:
            Dict[str, Any]: Estatísticas completas
        """
        # Validar acesso
        access_control_service.validate_company_access(
            db, user, company_id, "view_reports"
        )
        
        # Usar CRUD otimizado com índices compostos
        stats = crud_process.get_company_process_stats(db, company_id)
        
        # Adicionar metadados extras
        stats["requested_by_user_id"] = str(user.id)
        stats["is_superuser_request"] = user.is_superuser
        
        return stats
    
    def get_process_by_number_in_company(
        self,
        db: Session,
        company_id: UUID,
        process_number: str,
        user: User
    ) -> Process:
        """
        Buscar processo por número dentro da empresa.
        
        Usa índice único otimizado para performance máxima.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            process_number: Número do processo
            user: Usuário fazendo a busca
            
        Returns:
            Process: Processo encontrado
            
        Raises:
            HTTPException: Se não encontrado ou sem acesso
        """
        # Validar acesso à empresa
        access_control_service.validate_company_access(
            db, user, company_id, "read_processes"
        )
        
        # Busca otimizada com índice único
        process = crud_process.get_by_company_and_number(
            db, company_id=company_id, process_number=process_number
        )
        
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processo não encontrado nesta empresa"
            )
        
        return process
    
    def delete_process_with_validation(
        self,
        db: Session,
        process_id: UUID,
        company_id: UUID,
        user: User
    ) -> None:
        """
        Deletar processo com validações completas.
        
        Centraliza lógica de exclusão com auditoria.
        
        Args:
            db: Sessão do banco
            process_id: ID do processo
            company_id: ID da empresa
            user: Usuário executando a operação
        """
        # Validar acesso completo
        company, process = access_control_service.validate_company_process_delete_access(
            db, user, company_id, process_id
        )
        
        # TODO: Aqui poderia adicionar validações extras:
        # - Verificar se processo tem alertas associados
        # - Verificar se processo está sendo usado em relatórios
        # - Criar log de auditoria da exclusão
        
        # Deletar processo
        crud_process.delete(db, id=process_id)


# Instância global para uso nos endpoints
process_service = ProcessService() 