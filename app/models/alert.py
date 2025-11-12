from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Enum, TypeDecorator, VARCHAR
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


class AlertTypeType(TypeDecorator):
    """
    TypeDecorator para garantir que o SQLAlchemy use o valor do enum, não o nome.
    Usa String como impl para evitar problemas com o Enum interno do SQLAlchemy.
    """
    impl = VARCHAR(50)
    cache_ok = True
    
    def __init__(self, enum_class, **kwargs):
        # Remover parâmetros do Enum que não são necessários para String
        kwargs.pop('native_enum', None)
        kwargs.pop('name', None)
        super().__init__(**kwargs)
        self.enum_class = enum_class
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value  # Usar o valor do enum, não o nome
        if isinstance(value, str):
            return value
        return value
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # O valor vem do banco como string ('mudanca_status'), precisamos converter para o enum
        if isinstance(value, str):
            # Buscar o enum pelo valor
            for enum_member in self.enum_class:
                if enum_member.value == value:
                    return enum_member
            # Se não encontrar pelo valor, tentar pelo nome (fallback)
            try:
                return self.enum_class[value]
            except KeyError:
                # Se não encontrar nem pelo nome, tentar criar pelo valor
                return self.enum_class(value)
        # Se já for um enum, retornar direto
        if isinstance(value, self.enum_class):
            return value
        return value


class Alert(Base):
    """
    Modelo para alertas relacionados aos processos.
    """
    __tablename__ = "alert"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Informações do alerta
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    alert_type = Column(AlertTypeType(AlertType), nullable=False)
    
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