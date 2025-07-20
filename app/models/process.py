from sqlalchemy import Column, String, Text, Date, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.db.base_class import Base


class ProcessType(enum.Enum):
    """
    Tipos de processos de propriedade intelectual.
    """
    BRAND = "marca"
    PATENT = "patente"
    DESIGN = "desenho_industrial"
    SOFTWARE = "programa_computador"
    UTILITY_MODEL = "modelo_utilidade"
    

class ProcessStatus(enum.Enum):
    """
    Status dos processos.
    """
    PENDING = "pendente"
    ACTIVE = "ativo"
    GRANTED = "deferido"
    DENIED = "indeferido"
    EXPIRED = "expirado"
    ABANDONED = "abandonado"


class Process(Base):
    """
    Modelo para processos de propriedade intelectual.
    """
    __tablename__ = "process"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Informações básicas do processo
    process_number = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    short_title = Column(String(100), nullable=True)  # Abreviação do título para exibição
    description = Column(Text, nullable=True)
    
    # Tipo e status
    process_type = Column(Enum(ProcessType), nullable=False)
    status = Column(Enum(ProcessStatus), default=ProcessStatus.PENDING)
    
    # Datas importantes
    filing_date = Column(Date, nullable=True)  # Data de depósito
    publication_date = Column(Date, nullable=True)  # Data de publicação
    grant_date = Column(Date, nullable=True)  # Data de concessão
    expiry_date = Column(Date, nullable=True)  # Data de expiração
    
    # Informações do titular
    applicant_name = Column(String(500), nullable=True)  # Nome do depositante/titular
    applicant_document = Column(String(20), nullable=True)  # CPF/CNPJ do titular
    
    # Classificações
    nice_classification = Column(String(100), nullable=True)  # Para marcas
    ipc_classification = Column(String(100), nullable=True)  # Para patentes
    
    # Relacionamentos
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False)
    company = relationship("Company", back_populates="processes")
    alerts = relationship("Alert", back_populates="process")
    
    # Metadados
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        display_title = self.short_title or self.title[:30]
        return f"<Process(id='{self.id}', number='{self.process_number}', title='{display_title}...')>" 