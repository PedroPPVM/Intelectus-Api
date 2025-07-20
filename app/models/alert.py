from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.db.base_class import Base


class AlertType(enum.Enum):
    """
    Tipos de alertas do sistema.
    """
    STATUS_CHANGE = "mudanca_status"
    PUBLICATION = "publicacao"
    DEADLINE = "prazo"
    SIMILAR_PROCESS = "processo_similar"
    RENEWAL_DUE = "renovacao_vencimento"


class Alert(Base):
    """
    Modelo para alertas relacionados aos processos.
    """
    __tablename__ = "alert"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Informações do alerta
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    
    # Status
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    
    # Relacionamentos
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    user = relationship("User", back_populates="alerts")
    
    process_id = Column(UUID(as_uuid=True), ForeignKey("process.id"), nullable=True)
    process = relationship("Process", back_populates="alerts")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Alert(id='{self.id}', title='{self.title[:30]}...', type='{self.alert_type.value}')>" 