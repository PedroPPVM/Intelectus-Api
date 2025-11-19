import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.process import Process, ProcessType
from app.models.user import User
from app.schemas.process import ProcessCreate, ProcessUpdate, ProcessSummary
from app.crud import process as crud_process
from app.crud.crud_rpi_magazine import rpi_magazine as crud_rpi_magazine
from app.services.access_control_service import access_control_service
from app.services.scraping_service import scraping_service, BASE_URL
from app.services.alert_service import alert_service
from app.services import pdf_reader

# Logger para este módulo
logger = logging.getLogger('intelectus.process_service')
# Não definir nível aqui, usar o nível do root logger


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
        # Criar cópia do objeto para não modificar o original
        process_data_dict = process_data.dict()
        process_data_dict['company_id'] = company_id
        # Criar novo objeto ProcessCreate com company_id garantido
        from app.schemas.process import ProcessCreate
        process_data = ProcessCreate(**process_data_dict)
        
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
        
        # Guardar status anterior para criar alerta se mudou
        old_status = process.status
        
        # Verificar se há mudança de status no update_data
        update_dict = update_data.dict(exclude_unset=True)
        new_status = update_dict.get('status', old_status)
        has_status_change = 'status' in update_dict and old_status != new_status
        
        # Se há mudança de status ou outros campos, marcar como editado manualmente
        # Mas só se is_edited não foi explicitamente definido no update_data
        if update_dict and 'is_edited' not in update_dict:
            # Se há mudanças, marcar como editado manualmente
            update_data.is_edited = True
            logger.info(f"📝 Marcando processo {process.process_number} como editado manualmente (is_edited=True)")
        
        # Atualizar processo
        updated_process = crud_process.update(db, db_obj=process, obj_in=update_data)
        
        # Recarregar processo atualizado do banco para ter dados atualizados
        db.refresh(updated_process)
        
        # Criar alertas se houve mudança de status
        if has_status_change:
            update_details = {}
            
            # Criar alertas para todos os usuários da empresa
            try:
                alerts_created = alert_service.create_process_update_alert(
                    db=db,
                    process=updated_process,
                    old_status=old_status,
                    new_status=new_status,
                    update_details=update_details
                )
                logger.info(f"Criados {len(alerts_created)} alertas para processo {process.process_number}")
            except Exception as e:
                # Não falhar a atualização se criação de alerta falhar
                import traceback
                logger.warning(f"Erro ao criar alertas de atualização: {e}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
        
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
    
    def update_all_company_processes_from_latest_magazines(
        self,
        db: Session,
        company_id: UUID,
        user: User
    ) -> Dict[str, Any]:
        """
        Buscar atualizações de todos os processos da empresa.
        
        Verifica se estamos com a última revista lançada baixada e usada.
        Se não estiver, baixa e atualiza status que sejam necessários.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            user: Usuário executando a operação
            
        Returns:
            Dict com resumo das atualizações realizadas
        """
        # Validar acesso à empresa
        company = access_control_service.validate_company_access(
            db, user, company_id, "update_processes"
        )
        
        logger.info(f"🚀 Iniciando atualização de processos da empresa {company_id}")
        
        # Buscar todos os processos da empresa
        all_processes = crud_process.get_by_company(db, company_id=company_id, skip=0, limit=10000)
        logger.info(f"📊 Total de {len(all_processes)} processos encontrados para atualização")
        
        if not all_processes:
            return {
                "company_id": str(company_id),
                "total_processes": 0,
                "updated_processes": 0,
                "new_magazines": 0,
                "by_type": {}
            }
        
        # Agrupar processos por tipo
        processes_by_type: Dict[ProcessType, List[Process]] = {}
        for process in all_processes:
            if process.process_type not in processes_by_type:
                processes_by_type[process.process_type] = []
            processes_by_type[process.process_type].append(process)
        
        # Resultado agregado
        result = {
            "company_id": str(company_id),
            "total_processes": len(all_processes),
            "updated_processes": 0,
            "new_magazines": 0,
            "by_type": {}
        }
        
        # Para cada tipo de processo
        for process_type, processes in processes_by_type.items():
            type_result = {
                "process_type": process_type.value,
                "total": len(processes),
                "updated": 0,
                "magazine_created": False,
                "magazine_identifier": None
            }
            
            try:
                # Buscar links das últimas revistas disponíveis
                links = scraping_service._get_latest_links()
                latest_url = links.get(process_type)
                
                if not latest_url:
                    type_result["error"] = "Tipo de processo não suportado"
                    result["by_type"][process_type.value] = type_result
                    continue
                
                # Extrair identificador da última revista
                latest_identifier = scraping_service._extract_magazine_identifier(latest_url)
                
                # Verificar se já temos essa revista no banco
                existing_magazine = crud_rpi_magazine.get_by_type_and_identifier(
                    db, process_type, latest_identifier
                )
                
                # Se não temos, baixar e criar registro
                if not existing_magazine:
                    # Buscar soup para extrair data de publicação
                    import requests
                    from bs4 import BeautifulSoup
                    response = requests.get(BASE_URL)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Criar registro da revista
                    magazine, created = scraping_service.get_or_create_magazine(
                        db, process_type, latest_url, soup
                    )
                    type_result["magazine_created"] = created
                    type_result["magazine_identifier"] = magazine.magazine_identifier
                    result["new_magazines"] += 1
                else:
                    magazine = existing_magazine
                    type_result["magazine_identifier"] = magazine.magazine_identifier
                    
                    # OTIMIZAÇÃO: Se a revista já foi processada, verificar se precisa reprocessar
                    if magazine.processed_at is not None:
                        # Verificar se há processos editados manualmente ou não associados à revista
                        processes_need_update = [
                            p for p in processes 
                            if p.is_edited or p.magazine_id != magazine.id
                        ]
                        
                        logger.info(f"Revista já processada. Processos que precisam atualização: {len(processes_need_update)} (editados ou não associados)")
                        
                        if not processes_need_update:
                            # Todos os processos já estão atualizados e não foram editados manualmente
                            type_result["skipped"] = True
                            type_result["message"] = "Revista já processada e todos os processos já estão atualizados e sincronizados"
                            result["by_type"][process_type.value] = type_result
                            logger.info(f"⏭️ Pulando processamento - todos os processos já estão sincronizados")
                            continue
                        
                        logger.info(f"⚠️ Revista já processada, mas reprocessando {len(processes_need_update)} processos que precisam atualização")
                
                # Baixar PDF (se ainda não tiver sido baixado)
                logger.info(f"📥 Baixando PDF da revista...")
                pdf_path = scraping_service._download_pdf(latest_url)
                logger.info(f"✅ PDF baixado: {pdf_path}")
                
                try:
                    # Atualizar processos desse tipo
                    logger.info(f"Iniciando atualização de {len(processes)} processos do tipo {process_type.value}")
                    logger.info(f"Iniciando atualização de {len(processes)} processos do tipo {process_type.value}")
                    for process in processes:
                        try:
                            logger.debug(f"Buscando processo {process.process_number} na revista...")
                            # Buscar dados do processo no PDF
                            if process_type == ProcessType.BRAND:
                                data = pdf_reader.search_status_marcas(process.process_number, pdf_path)
                            elif process_type == ProcessType.PATENT:
                                data = pdf_reader.search_status_patentes(process.process_number, pdf_path)
                            elif process_type == ProcessType.DESIGN:
                                data = pdf_reader.search_status_desenhos_industriais(process.process_number, pdf_path)
                            elif process_type == ProcessType.SOFTWARE:
                                data = pdf_reader.search_status_programa_de_computador(process.process_number, pdf_path)
                            else:
                                data = None
                            
                            if data:
                                status_novo = data.get('status')
                                old_status = process.status
                                logger.debug(f"Processo {process.process_number} encontrado na revista. Status atual: '{old_status}', Status na revista: '{status_novo}'")
                                # Verificar se precisa atualizar
                                update_data = {}
                                has_status_change = False
                                has_any_change = False
                                
                                # SEMPRE atualizar status para o da revista se disponível
                                # Isso garante que mesmo status editados manualmente sejam resetados
                                if status_novo:
                                    # Verificar se o status realmente mudou
                                    if status_novo != process.status:
                                        has_status_change = True
                                        has_any_change = True
                                        logger.info(f"🔄 Mudança de status detectada para processo {process.process_number}: '{old_status}' -> '{status_novo}'")
                                        # Atualizar status para o da revista (resetar edições manuais)
                                        update_data['status'] = status_novo
                                        logger.info(f"📝 Atualizando processo {process.process_number} com status da revista: '{status_novo}' (status anterior: '{old_status}')")
                                    else:
                                        logger.debug(f"Status do processo {process.process_number} já está atualizado: {status_novo}")
                                
                                # Verificar se magazine_id precisa ser atualizado
                                if process.magazine_id != magazine.id:
                                    has_any_change = True
                                    update_data['magazine_id'] = magazine.id
                                
                                # Verificar se is_edited precisa ser atualizado (sempre marcar como False quando atualizado via scraping)
                                if process.is_edited:
                                    has_any_change = True
                                    update_data['is_edited'] = False
                                
                                # Só atualizar e contar se houver mudança real
                                if has_any_change:
                                    # Garantir que is_edited seja False quando atualizado via scraping
                                    if 'is_edited' not in update_data:
                                        update_data['is_edited'] = False
                                    
                                    logger.info(f"💾 Salvando atualização do processo {process.process_number}: {update_data}")
                                    # Atualizar processo (CRUD já faz commit automaticamente)
                                    updated_process = crud_process.update(
                                        db, 
                                        db_obj=process, 
                                        obj_in=ProcessUpdate(**update_data)
                                    )
                                    
                                    # Recarregar processo atualizado
                                    db.refresh(updated_process)
                                    logger.info(f"✅ Processo {process.process_number} atualizado com sucesso. Novo status: '{updated_process.status}', is_edited: {updated_process.is_edited}")
                                    
                                    # Criar alertas se houve mudança de status
                                    logger.debug(f"Verificando se deve criar alertas: has_status_change={has_status_change}, old_status='{old_status}', new_status='{status_novo}'")
                                    if has_status_change:
                                        try:
                                            logger.info(f"🔔 Criando alertas para mudança de status do processo {process.process_number}: '{old_status}' -> '{status_novo}'")
                                            update_details = {
                                                'magazine_identifier': magazine.magazine_identifier
                                            }
                                            alerts_created = alert_service.create_process_update_alert(
                                                db=db,
                                                process=updated_process,
                                                old_status=old_status,
                                                new_status=status_novo,
                                                update_details=update_details
                                            )
                                            logger.info(f"✅ Criados {len(alerts_created)} alertas para processo {process.process_number}")
                                            if len(alerts_created) == 0:
                                                logger.warning(f"⚠️ Nenhum alerta foi criado para processo {process.process_number}. Verifique se há memberships ativos na empresa {process.company_id}.")
                                        except Exception as e:
                                            # Não falhar a atualização se criação de alerta falhar
                                            import traceback
                                            logger.error(f"❌ Erro ao criar alerta para processo {process.process_number}: {e}")
                                            logger.debug(f"Traceback: {traceback.format_exc()}")
                                    else:
                                        logger.debug(f"⏭️ Não criando alerta: status não mudou (old='{old_status}', new='{status_novo}')")
                                    
                                    # Contar apenas se houve mudança real
                                    type_result["updated"] += 1
                                    result["updated_processes"] += 1
                                else:
                                    logger.debug(f"⏭️ Processo {process.process_number} já está sincronizado (sem mudanças)")
                            else:
                                logger.warning(f"⚠️ Processo {process.process_number} não encontrado na revista")
                        except Exception as e:
                            # Continuar com próximo processo em caso de erro
                            logger.error(f"Erro ao atualizar processo {process.process_number}: {e}")
                            continue
                    
                    # Atualizar processed_at da revista
                    from app.schemas.rpi_magazine import RPIMagazineUpdate
                    crud_rpi_magazine.update(
                        db,
                        db_obj=magazine,
                        obj_in=RPIMagazineUpdate(processed_at=datetime.now(timezone.utc))
                    )
                    
                finally:
                    # Remover PDF após processamento
                    scraping_service._remove_pdf(pdf_path)
                
            except Exception as e:
                type_result["error"] = str(e)
                logger.error(f"Erro ao processar tipo {process_type.value}: {e}")
            
            result["by_type"][process_type.value] = type_result
        
        return result
    
    def update_company_processes_by_type_from_latest_magazines(
        self,
        db: Session,
        company_id: UUID,
        user: User,
        process_type: Optional[ProcessType] = None
    ) -> Dict[str, Any]:
        """
        Buscar atualizações de processos da empresa por tipo específico.
        
        Se process_type for None, atualiza todos os tipos (comportamento igual a 
        update_all_company_processes_from_latest_magazines).
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            user: Usuário executando a operação
            process_type: Tipo de processo a atualizar (opcional, se None atualiza todos)
            
        Returns:
            Dict com resumo das atualizações realizadas
        """
        logger.info(f"🚀 MÉTODO CHAMADO: update_company_processes_by_type_from_latest_magazines")
        logger.debug(f"Company ID: {company_id}, Process Type: {process_type}")
        
        # Validar acesso à empresa
        company = access_control_service.validate_company_access(
            db, user, company_id, "update_processes"
        )
        
        logger.debug(f"✅ Acesso validado para empresa {company_id}")
        
        # Buscar processos da empresa
        if process_type:
            # Buscar apenas processos do tipo especificado
            logger.debug(f"Buscando processos do tipo {process_type.value}")
            all_processes = crud_process.get_by_company_and_type(
                db, company_id=company_id, process_type=process_type.value, skip=0, limit=10000
            )
        else:
            # Buscar todos os processos
            logger.debug(f"Buscando todos os processos")
            all_processes = crud_process.get_by_company(db, company_id=company_id, skip=0, limit=10000)
        
        logger.info(f"📊 Total de {len(all_processes)} processos encontrados para atualização")
        
        if not all_processes:
            return {
                "company_id": str(company_id),
                "process_type": process_type.value if process_type else "ALL",
                "total_processes": 0,
                "updated_processes": 0,
                "new_magazines": 0,
                "by_type": {}
            }
        
        # Agrupar processos por tipo
        processes_by_type: Dict[ProcessType, List[Process]] = {}
        for process in all_processes:
            if process.process_type not in processes_by_type:
                processes_by_type[process.process_type] = []
            processes_by_type[process.process_type].append(process)
        
        # Se process_type foi especificado, filtrar apenas esse tipo
        if process_type:
            processes_by_type = {process_type: processes_by_type.get(process_type, [])}
        
        # Resultado agregado
        result = {
            "company_id": str(company_id),
            "process_type": process_type.value if process_type else "ALL",
            "total_processes": len(all_processes),
            "updated_processes": 0,
            "new_magazines": 0,
            "by_type": {}
        }
        
        # Para cada tipo de processo
        logger.info(f"Processando {len(processes_by_type)} tipos de processos")
        for proc_type, processes in processes_by_type.items():
            logger.info(f"📋 Processando tipo {proc_type.value} com {len(processes)} processos")
            type_result = {
                "process_type": proc_type.value,
                "total": len(processes),
                "updated": 0,
                "magazine_created": False,
                "magazine_identifier": None
            }
            
            try:
                # Buscar links das últimas revistas disponíveis
                logger.debug(f"Buscando links das últimas revistas...")
                links = scraping_service._get_latest_links()
                latest_url = links.get(proc_type)
                
                if not latest_url:
                    logger.warning(f"⚠️ Tipo de processo {proc_type.value} não suportado")
                    type_result["error"] = "Tipo de processo não suportado"
                    result["by_type"][proc_type.value] = type_result
                    continue
                
                logger.debug(f"✅ URL da última revista encontrada: {latest_url}")
                
                # Extrair identificador da última revista
                latest_identifier = scraping_service._extract_magazine_identifier(latest_url)
                logger.debug(f"Identificador da revista: {latest_identifier}")
                
                # Verificar se já temos essa revista no banco
                existing_magazine = crud_rpi_magazine.get_by_type_and_identifier(
                    db, proc_type, latest_identifier
                )
                
                # Se não temos, baixar e criar registro
                if not existing_magazine:
                    logger.info(f"📥 Revista não encontrada no banco. Criando registro...")
                    # Buscar soup para extrair data de publicação
                    import requests
                    from bs4 import BeautifulSoup
                    response = requests.get(BASE_URL)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Criar registro da revista
                    magazine, created = scraping_service.get_or_create_magazine(
                        db, proc_type, latest_url, soup
                    )
                    type_result["magazine_created"] = created
                    type_result["magazine_identifier"] = magazine.magazine_identifier
                    result["new_magazines"] += 1
                    logger.info(f"✅ Revista criada/obtida: {magazine.magazine_identifier}")
                else:
                    magazine = existing_magazine
                    type_result["magazine_identifier"] = magazine.magazine_identifier
                    logger.debug(f"✅ Revista já existe no banco: {magazine.magazine_identifier}")
                    
                    # OTIMIZAÇÃO: Se a revista já foi processada, verificar se precisa reprocessar
                    if magazine.processed_at is not None:
                        # Verificar se há processos editados manualmente ou não associados à revista
                        processes_need_update = [
                            p for p in processes 
                            if p.is_edited or p.magazine_id != magazine.id
                        ]
                        
                        logger.info(f"Revista já processada. Processos que precisam atualização: {len(processes_need_update)} (editados ou não associados)")
                        
                        if not processes_need_update:
                            # Todos os processos já estão atualizados e não foram editados manualmente
                            type_result["skipped"] = True
                            type_result["message"] = "Revista já processada e todos os processos já estão atualizados e sincronizados"
                            result["by_type"][proc_type.value] = type_result
                            logger.info(f"⏭️ Pulando processamento - todos os processos já estão sincronizados")
                            continue
                        
                        logger.info(f"⚠️ Revista já processada, mas reprocessando {len(processes_need_update)} processos que precisam atualização")
                
                # Baixar PDF (se ainda não tiver sido baixado)
                logger.info(f"📥 Baixando PDF da revista...")
                pdf_path = scraping_service._download_pdf(latest_url)
                logger.info(f"✅ PDF baixado: {pdf_path}")
                
                try:
                    # Atualizar processos desse tipo
                    logger.info(f"Iniciando atualização de {len(processes)} processos do tipo {proc_type.value}")
                    for process in processes:
                        try:
                            logger.debug(f"Buscando processo {process.process_number} na revista...")
                            # Buscar dados do processo no PDF
                            if proc_type == ProcessType.BRAND:
                                data = pdf_reader.search_status_marcas(process.process_number, pdf_path)
                            elif proc_type == ProcessType.PATENT:
                                data = pdf_reader.search_status_patentes(process.process_number, pdf_path)
                            elif proc_type == ProcessType.DESIGN:
                                data = pdf_reader.search_status_desenhos_industriais(process.process_number, pdf_path)
                            elif proc_type == ProcessType.SOFTWARE:
                                data = pdf_reader.search_status_programa_de_computador(process.process_number, pdf_path)
                            else:
                                data = None
                            
                            if data:
                                # Verificar se precisa atualizar
                                status_novo = data.get('status')
                                old_status = process.status
                                update_data = {}
                                has_status_change = False
                                has_any_change = False
                                
                                # SEMPRE atualizar status para o da revista se disponível
                                # Isso garante que mesmo status editados manualmente sejam resetados
                                if status_novo:
                                    # Verificar se o status realmente mudou
                                    if status_novo != process.status:
                                        has_status_change = True
                                        has_any_change = True
                                        logger.info(f"🔄 Mudança de status detectada para processo {process.process_number}: '{old_status}' -> '{status_novo}'")
                                        # Atualizar status para o da revista (resetar edições manuais)
                                        update_data['status'] = status_novo
                                        logger.info(f"📝 Atualizando processo {process.process_number} com status da revista: '{status_novo}' (status anterior: '{old_status}')")
                                    else:
                                        logger.debug(f"Status do processo {process.process_number} já está atualizado: {status_novo}")
                                
                                # Verificar se magazine_id precisa ser atualizado
                                if process.magazine_id != magazine.id:
                                    has_any_change = True
                                    update_data['magazine_id'] = magazine.id
                                
                                # Verificar se is_edited precisa ser atualizado (sempre marcar como False quando atualizado via scraping)
                                if process.is_edited:
                                    has_any_change = True
                                    update_data['is_edited'] = False
                                
                                # Só atualizar e contar se houver mudança real
                                if has_any_change:
                                    # Garantir que is_edited seja False quando atualizado via scraping
                                    if 'is_edited' not in update_data:
                                        update_data['is_edited'] = False
                                    
                                    logger.info(f"💾 Salvando atualização do processo {process.process_number}: {update_data}")
                                    # Atualizar processo (CRUD já faz commit automaticamente)
                                    updated_process = crud_process.update(
                                        db, 
                                        db_obj=process, 
                                        obj_in=ProcessUpdate(**update_data)
                                    )
                                    
                                    # Recarregar processo atualizado
                                    db.refresh(updated_process)
                                    logger.info(f"✅ Processo {process.process_number} atualizado com sucesso. Novo status: '{updated_process.status}', is_edited: {updated_process.is_edited}")
                                    
                                    # Criar alertas se houve mudança de status
                                    logger.debug(f"Verificando se deve criar alertas: has_status_change={has_status_change}, old_status='{old_status}', new_status='{status_novo}'")
                                    if has_status_change:
                                        try:
                                            logger.info(f"🔔 Criando alertas para mudança de status do processo {process.process_number}: '{old_status}' -> '{status_novo}'")
                                            update_details = {
                                                'magazine_identifier': magazine.magazine_identifier
                                            }
                                            alerts_created = alert_service.create_process_update_alert(
                                                db=db,
                                                process=updated_process,
                                                old_status=old_status,
                                                new_status=status_novo,
                                                update_details=update_details
                                            )
                                            logger.info(f"✅ Criados {len(alerts_created)} alertas para processo {process.process_number}")
                                            if len(alerts_created) == 0:
                                                logger.warning(f"⚠️ Nenhum alerta foi criado para processo {process.process_number}. Verifique se há memberships ativos na empresa {process.company_id}.")
                                        except Exception as e:
                                            # Não falhar a atualização se criação de alerta falhar
                                            import traceback
                                            logger.error(f"❌ Erro ao criar alerta para processo {process.process_number}: {e}")
                                            logger.debug(f"Traceback: {traceback.format_exc()}")
                                    else:
                                        logger.debug(f"⏭️ Não criando alerta: status não mudou (old='{old_status}', new='{status_novo}')")
                                    
                                    # Contar apenas se houve mudança real
                                    type_result["updated"] += 1
                                    result["updated_processes"] += 1
                                else:
                                    logger.debug(f"⏭️ Processo {process.process_number} já está sincronizado (sem mudanças)")
                            else:
                                logger.warning(f"⚠️ Processo {process.process_number} não encontrado na revista")
                        except Exception as e:
                            # Continuar com próximo processo em caso de erro
                            logger.error(f"Erro ao atualizar processo {process.process_number}: {e}")
                            continue
                    
                    # Atualizar processed_at da revista
                    from app.schemas.rpi_magazine import RPIMagazineUpdate
                    crud_rpi_magazine.update(
                        db,
                        db_obj=magazine,
                        obj_in=RPIMagazineUpdate(processed_at=datetime.now(timezone.utc))
                    )
                    
                finally:
                    # Remover PDF após processamento
                    scraping_service._remove_pdf(pdf_path)
                
            except Exception as e:
                type_result["error"] = str(e)
                logger.error(f"Erro ao processar tipo {proc_type.value}: {e}")
                import traceback
                logger.debug(f"Traceback: {traceback.format_exc()}")
            
            result["by_type"][proc_type.value] = type_result
        
        return result


# Instância global para uso nos endpoints
process_service = ProcessService() 