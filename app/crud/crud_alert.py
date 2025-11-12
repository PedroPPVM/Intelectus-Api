from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertUpdate


class CRUDAlert:
    """
    Operações CRUD para o modelo Alert.
    """
    
    def create(self, db: Session, *, obj_in: AlertCreate) -> Alert:
        """
        Criar um novo alerta.
        """
        import logging
        logger = logging.getLogger('intelectus.crud_alert')
        
        logger.debug(f"Criando alerta: title='{obj_in.title}', type={obj_in.alert_type}, user_id={obj_in.user_id}, process_id={obj_in.process_id}")
        
        db_alert = Alert(
            title=obj_in.title,
            message=obj_in.message,
            alert_type=obj_in.alert_type,
            user_id=obj_in.user_id,
            process_id=obj_in.process_id,
            is_read=False,
            is_dismissed=False
        )
        
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        
        logger.debug(f"Alerta criado com sucesso: ID={db_alert.id}")
        return db_alert
    
    def get(self, db: Session, id: UUID) -> Optional[Alert]:
        """
        Buscar alerta por ID.
        """
        return db.query(Alert).filter(Alert.id == id).first()
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Alert]:
        """
        Buscar múltiplos alertas com paginação.
        """
        return db.query(Alert).offset(skip).limit(limit).all()
    
    def get_by_user(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Alert]:
        """
        Buscar alertas de um usuário específico.
        """
        return (
            db.query(Alert)
            .filter(Alert.user_id == user_id)
            .order_by(Alert.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_unread_by_user(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Alert]:
        """
        Buscar alertas não lidos de um usuário.
        """
        return (
            db.query(Alert)
            .filter(Alert.user_id == user_id, Alert.is_read == False)
            .order_by(Alert.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_process(
        self, db: Session, process_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Alert]:
        """
        Buscar alertas relacionados a um processo específico.
        """
        return (
            db.query(Alert)
            .filter(Alert.process_id == process_id)
            .order_by(Alert.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_type(
        self, db: Session, alert_type, skip: int = 0, limit: int = 100
    ) -> List[Alert]:
        """
        Buscar alertas por tipo.
        
        Args:
            alert_type: Pode ser string ou AlertType enum
        """
        # Converter string para enum se necessário
        from app.models.alert import AlertType
        if isinstance(alert_type, str):
            try:
                alert_type = AlertType(alert_type)
            except ValueError:
                # Tipo inválido, retornar lista vazia
                return []
        
        return (
            db.query(Alert)
            .filter(Alert.alert_type == alert_type)
            .order_by(Alert.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_unread_by_user(self, db: Session, user_id: UUID) -> int:
        """
        Contar alertas não lidos de um usuário.
        """
        return (
            db.query(Alert)
            .filter(Alert.user_id == user_id, Alert.is_read == False)
            .count()
        )
    
    def update(
        self, db: Session, *, db_obj: Alert, obj_in: AlertUpdate
    ) -> Alert:
        """
        Atualizar um alerta existente.
        
        Se is_dismissed for marcado como True, também marca como read.
        """
        update_data = obj_in.dict(exclude_unset=True)
        
        # Se está marcando como dismissed, também marcar como read
        if update_data.get('is_dismissed') is True and not db_obj.is_read:
            update_data['is_read'] = True
            if 'read_at' not in update_data:
                update_data['read_at'] = datetime.utcnow()
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def mark_as_read(self, db: Session, *, id: UUID) -> Optional[Alert]:
        """
        Marcar alerta como lido.
        """
        obj = db.query(Alert).filter(Alert.id == id).first()
        if obj and not obj.is_read:
            obj.is_read = True
            obj.read_at = datetime.utcnow()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj
    
    def mark_as_dismissed(self, db: Session, *, id: UUID) -> Optional[Alert]:
        """
        Marcar alerta como descartado.
        
        Quando um alerta é descartado, também é marcado como lido,
        pois se o usuário descartou, significa que ele leu.
        """
        obj = db.query(Alert).filter(Alert.id == id).first()
        if obj:
            obj.is_dismissed = True
            # Se descartou, também leu
            if not obj.is_read:
                obj.is_read = True
                obj.read_at = datetime.utcnow()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj
    
    def mark_all_as_read_by_user(self, db: Session, *, user_id: UUID) -> int:
        """
        Marcar todos os alertas de um usuário como lidos.
        """
        count = (
            db.query(Alert)
            .filter(Alert.user_id == user_id, Alert.is_read == False)
            .update({"is_read": True, "read_at": datetime.utcnow()})
        )
        db.commit()
        return count
    
    def delete(self, db: Session, *, id: UUID) -> Optional[Alert]:
        """
        Deletar um alerta.
        """
        obj = db.query(Alert).filter(Alert.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def delete_old_alerts(self, db: Session, *, days: int = 30) -> int:
        """
        Deletar alertas antigos (mais de X dias).
        """
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        count = (
            db.query(Alert)
            .filter(Alert.created_at < cutoff_date, Alert.is_dismissed == True)
            .count()
        )
        
        (
            db.query(Alert)
            .filter(Alert.created_at < cutoff_date, Alert.is_dismissed == True)
            .delete()
        )
        
        db.commit()
        return count


# Instância global para uso nos endpoints
alert = CRUDAlert() 