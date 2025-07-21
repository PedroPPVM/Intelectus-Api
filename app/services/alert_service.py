from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertType
from app.models.user import User
from app.models.process import Process
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse
from app.crud import alert as crud_alert
from app.services.access_control_service import access_control_service


class AlertService:
    """
    Service para centralizar todas as regras de negócio de alertas.
    
    🎯 Objetivo: Padronizar sistema de notificações, centralizar lógicas
    de matching e preparar base para scraping automático.
    
    Roadmap Fase 3.2 - Etapa 4 (Média Prioridade)
    """
    
    def create_alert_with_validation(
        self,
        db: Session,
        alert_data: AlertCreate,
        user: User
    ) -> Alert:
        """
        Criar alerta com validações completas.
        
        Usado principalmente pelo sistema de scraping para notificar usuários.
        
        Args:
            db: Sessão do banco
            alert_data: Dados do alerta
            user: Usuário criando (geralmente superusuário/sistema)
            
        Returns:
            Alert: Alerta criado
            
        Raises:
            HTTPException: Se validações falharem
        """
        # Apenas superusuários criam alertas (sistema de scraping)
        access_control_service.validate_superuser(user)
        
        # Validar regras de negócio
        self.validate_alert_business_rules(alert_data)
        
        # Verificar se processo existe (se fornecido)
        if alert_data.process_id:
            # Usar access_control_service para validação centralizada
            # Como é sistema, passamos o superusuário que já foi validado
            access_control_service.validate_process_access(
                db, user, alert_data.process_id, "read_processes"
            )
        
        # Criar alerta
        alert = crud_alert.create(db, obj_in=alert_data)
        
        return alert
    
    def get_user_alerts_with_filters(
        self,
        db: Session,
        user: User,
        filters: Dict[str, Any]
    ) -> List[Alert]:
        """
        Obter alertas do usuário com filtros.
        
        Centraliza lógica de acesso e filtros dos endpoints.
        
        Args:
            db: Sessão do banco
            user: Usuário fazendo a consulta
            filters: Dicionário com filtros (unread_only, alert_type, skip, limit)
            
        Returns:
            List[Alert]: Alertas filtrados
        """
        # Extrair parâmetros
        skip = filters.get('skip', 0)
        limit = filters.get('limit', 100)
        unread_only = filters.get('unread_only', False)
        alert_type = filters.get('alert_type')
        
        if user.is_superuser:
            # Superusuário pode ver todos os alertas
            if alert_type:
                return crud_alert.get_by_type(db, alert_type=alert_type, skip=skip, limit=limit)
            else:
                return crud_alert.get_multi(db, skip=skip, limit=limit)
        else:
            # Usuário normal só vê seus alertas
            if unread_only:
                alerts = crud_alert.get_unread_by_user(db, user_id=user.id, skip=skip, limit=limit)
            else:
                alerts = crud_alert.get_by_user(db, user_id=user.id, skip=skip, limit=limit)
            
            # Aplicar filtro por tipo se fornecido
            if alert_type:
                alerts = [a for a in alerts if a.alert_type.value == alert_type]
            
            return alerts
    
    def mark_alert_as_read_with_audit(
        self,
        db: Session,
        alert_id: UUID,
        user: User
    ) -> Alert:
        """
        Marcar alerta como lido com auditoria.
        
        Centraliza lógica que está duplicada nos endpoints.
        
        Args:
            db: Sessão do banco
            alert_id: ID do alerta
            user: Usuário marcando como lido
            
        Returns:
            Alert: Alerta atualizado
            
        Raises:
            HTTPException: Se não encontrado ou sem permissão
        """
        # Validar acesso ao alerta
        alert = access_control_service.validate_alert_access(db, user, alert_id)
        
        # Marcar como lido
        updated_alert = crud_alert.mark_as_read(db, id=alert_id)
        
        if not updated_alert:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao marcar alerta como lido"
            )
        
        return updated_alert
    
    def mark_alert_as_dismissed_with_audit(
        self,
        db: Session,
        alert_id: UUID,
        user: User
    ) -> Alert:
        """
        Marcar alerta como descartado com auditoria.
        
        Centraliza lógica duplicada nos endpoints.
        
        Args:
            db: Sessão do banco
            alert_id: ID do alerta
            user: Usuário descartando o alerta
            
        Returns:
            Alert: Alerta atualizado
        """
        # Validar acesso ao alerta
        alert = access_control_service.validate_alert_access(db, user, alert_id)
        
        # Marcar como descartado
        updated_alert = crud_alert.mark_as_dismissed(db, id=alert_id)
        
        if not updated_alert:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao descartar alerta"
            )
        
        return updated_alert
    
    def get_process_related_alerts(
        self,
        db: Session,
        process_id: UUID,
        user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[Alert]:
        """
        Obter alertas relacionados a um processo específico.
        
        Centraliza lógica de acesso e filtragem por processo.
        
        Args:
            db: Sessão do banco
            process_id: ID do processo
            user: Usuário fazendo a consulta
            skip: Registros para pular
            limit: Máximo de registros
            
        Returns:
            List[Alert]: Alertas do processo
        """
        # Validar acesso ao processo
        process = access_control_service.validate_process_access(
            db, user, process_id, "read_processes"
        )
        
        # Buscar alertas do processo
        alerts = crud_alert.get_by_process(db, process_id=process_id, skip=skip, limit=limit)
        
        # Filtrar apenas alertas do usuário atual (exceto superusuários)
        if not user.is_superuser:
            alerts = [alert for alert in alerts if alert.user_id == user.id]
        
        return alerts
    
    def create_process_match_alert(
        self,
        db: Session,
        process_id: UUID,
        user_id: UUID,
        match_details: Dict[str, Any],
        alert_type: AlertType = AlertType.SIMILAR_PROCESS
    ) -> Alert:
        """
        Criar alerta de matching de processo.
        
        Usado pelo sistema de scraping para notificar sobre matches.
        
        Args:
            db: Sessão do banco
            process_id: ID do processo relacionado
            user_id: ID do usuário a ser notificado
            match_details: Detalhes do match encontrado
            alert_type: Tipo do alerta
            
        Returns:
            Alert: Alerta criado
        """
        # Criar dados do alerta
        title = f"Processo similar encontrado: {match_details.get('process_number', 'N/A')}"
        
        message_parts = [
            f"Foi encontrado um processo similar ao seu:",
            f"• Número: {match_details.get('process_number', 'N/A')}",
            f"• Título: {match_details.get('title', 'N/A')}",
            f"• Tipo: {match_details.get('process_type', 'N/A')}",
            f"• Depositante: {match_details.get('depositor', 'N/A')}",
            f"• Status: {match_details.get('status', 'N/A')}",
        ]
        
        if 'similarity_score' in match_details:
            message_parts.append(f"• Similaridade: {match_details['similarity_score']:.1%}")
        
        alert_data = AlertCreate(
            title=title,
            message="\n".join(message_parts),
            alert_type=alert_type,
            user_id=user_id,
            process_id=process_id
        )
        
        # Criar alerta diretamente (sistema interno)
        alert = crud_alert.create(db, obj_in=alert_data)
        
        return alert
    
    def bulk_mark_alerts_read(
        self,
        db: Session,
        user: User,
        alert_ids: List[UUID]
    ) -> int:
        """
        Marcar múltiplos alertas como lidos em lote.
        
        Otimiza operações em massa.
        
        Args:
            db: Sessão do banco
            user: Usuário executando a operação
            alert_ids: Lista de IDs dos alertas
            
        Returns:
            int: Número de alertas marcados como lidos
        """
        marked_count = 0
        
        for alert_id in alert_ids:
            try:
                # Validar acesso a cada alerta
                access_control_service.validate_alert_access(db, user, alert_id)
                
                # Marcar como lido
                updated_alert = crud_alert.mark_as_read(db, id=alert_id)
                if updated_alert:
                    marked_count += 1
                    
            except HTTPException:
                # Ignorar alertas sem acesso (não parar o processo)
                continue
        
        return marked_count
    
    def get_alert_statistics(
        self,
        db: Session,
        user_id: UUID,
        user: User
    ) -> Dict[str, Any]:
        """
        Obter estatísticas de alertas do usuário.
        
        Centraliza lógica de dashboard de alertas.
        
        Args:
            db: Sessão do banco
            user_id: ID do usuário (pode ser diferente de user se superusuário)
            user: Usuário fazendo a consulta
            
        Returns:
            Dict[str, Any]: Estatísticas de alertas
        """
        # Verificar se pode consultar alertas de outro usuário
        if not user.is_superuser and user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: você só pode ver suas próprias estatísticas"
            )
        
        # Contar alertas não lidos
        unread_count = crud_alert.count_unread_by_user(db, user_id=user_id)
        
        # Obter todos os alertas do usuário para estatísticas
        all_alerts = crud_alert.get_by_user(db, user_id=user_id, skip=0, limit=1000)
        
        # Estatísticas por tipo
        type_stats = {}
        for alert_type in AlertType:
            count = len([a for a in all_alerts if a.alert_type == alert_type])
            type_stats[alert_type.value] = count
        
        # Estatísticas por status
        read_count = len([a for a in all_alerts if a.is_read])
        dismissed_count = len([a for a in all_alerts if a.is_dismissed])
        
        return {
            "user_id": str(user_id),
            "total_alerts": len(all_alerts),
            "unread_count": unread_count,
            "read_count": read_count,
            "dismissed_count": dismissed_count,
            "by_type": type_stats,
            "requested_by_user_id": str(user.id),
            "is_superuser_request": user.is_superuser,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def update_alert_with_validation(
        self,
        db: Session,
        alert_id: UUID,
        update_data: AlertUpdate,
        user: User
    ) -> Alert:
        """
        Atualizar alerta com validações.
        
        Centraliza lógica de atualização de alertas.
        
        Args:
            db: Sessão do banco
            alert_id: ID do alerta
            update_data: Dados para atualização
            user: Usuário executando a operação
            
        Returns:
            Alert: Alerta atualizado
        """
        # Validar acesso ao alerta
        alert = access_control_service.validate_alert_access(db, user, alert_id)
        
        # Atualizar alerta
        updated_alert = crud_alert.update(db, db_obj=alert, obj_in=update_data)
        
        return updated_alert
    
    def delete_alert_with_validation(
        self,
        db: Session,
        alert_id: UUID,
        user: User
    ) -> None:
        """
        Deletar alerta com validações.
        
        Centraliza lógica de exclusão de alertas.
        
        Args:
            db: Sessão do banco
            alert_id: ID do alerta
            user: Usuário executando a operação
        """
        # Validar acesso ao alerta
        alert = access_control_service.validate_alert_access(db, user, alert_id)
        
        # Deletar alerta
        crud_alert.delete(db, id=alert_id)
    
    def validate_alert_business_rules(
        self,
        alert_data: AlertCreate | AlertUpdate
    ) -> None:
        """
        Validar regras de negócio específicas de alertas.
        
        Centraliza validações de alertas.
        
        Args:
            alert_data: Dados do alerta para validar
            
        Raises:
            HTTPException: Se alguma regra for violada
        """
        # Validação de título
        if hasattr(alert_data, 'title') and alert_data.title:
            title = alert_data.title.strip()
            
            if len(title) < 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Título do alerta deve ter pelo menos 5 caracteres"
                )
            
            if len(title) > 500:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Título do alerta deve ter no máximo 500 caracteres"
                )
        
        # Validação de mensagem
        if hasattr(alert_data, 'message') and alert_data.message:
            message = alert_data.message.strip()
            
            if len(message) < 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mensagem do alerta deve ter pelo menos 10 caracteres"
                )
            
            if len(message) > 2000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mensagem do alerta deve ter no máximo 2000 caracteres"
                )
    
    def get_alert_with_access_validation(
        self,
        db: Session,
        alert_id: UUID,
        user: User
    ) -> Alert:
        """
        Obter alerta com validação de acesso.
        
        Wrapper conveniente que combina busca + validação.
        
        Args:
            db: Sessão do banco
            alert_id: ID do alerta
            user: Usuário fazendo a consulta
            
        Returns:
            Alert: Alerta se acesso válido
        """
        return access_control_service.validate_alert_access(db, user, alert_id)
    
    def mark_all_user_alerts_as_read(
        self,
        db: Session,
        user: User
    ) -> int:
        """
        Marcar todos os alertas de um usuário como lidos.
        
        Funcionalidade útil para "limpar" notificações.
        
        Args:
            db: Sessão do banco
            user: Usuário executando a operação
            
        Returns:
            int: Número de alertas marcados como lidos
        """
        # Marcar todos como lidos
        count = crud_alert.mark_all_as_read_by_user(db, user_id=user.id)
        
        return count


# Instância global para uso nos endpoints
alert_service = AlertService() 