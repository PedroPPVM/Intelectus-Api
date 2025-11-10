from sqlalchemy import Column, String, Date, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.db.base_class import Base


class ProcessType(enum.Enum):
    """
    Tipos de processos de propriedade intelectual.
    Alinhado com o schema planejado.
    """
    BRAND = "BRAND"
    PATENT = "PATENT" 
    DESIGN = "DESIGN"
    SOFTWARE = "SOFTWARE"


class ProcessSituation(enum.Enum):
    """
    Situação atual do processo - mais específico que status.
    """
    FILED = "FILED"
    PUBLISHED = "PUBLISHED"  
    UNDER_EXAMINATION = "UNDER_EXAMINATION"
    OPPOSED = "OPPOSED"
    GRANTED = "GRANTED"
    EXPIRED = "EXPIRED"
    LAPSED = "LAPSED"
    RENEWED = "RENEWED"


class Process(Base):
    """
    Modelo para processos de propriedade intelectual.
    Alinhado com o schema planejado e otimizado para scraping.
    """
    __tablename__ = "process"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Relacionamento com empresa
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False)
    
    # Identificação do processo
    process_type = Column(Enum(ProcessType, name="processtype", native_enum=True), nullable=False)
    process_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(1000), nullable=False)
    
    # Depositante/Requerente
    depositor = Column(String(500), nullable=True)  # Nome do depositante
    cnpj_depositor = Column(String(20), nullable=True)  # CNPJ se pessoa jurídica
    cpf_depositor = Column(String(15), nullable=True)   # CPF se pessoa física
    
    # Procurador/Representante Legal
    attorney = Column(String(500), nullable=True)
    
    # Datas importantes
    deposit_date = Column(Date, nullable=True)      # Data de depósito
    concession_date = Column(Date, nullable=True)   # Data de concessão
    validity_date = Column(Date, nullable=True)     # Data de validade/vigência
    
    # Status e situação
    status = Column(String(1000), nullable=False)
    situation = Column(Enum(ProcessSituation, name="processsituation", native_enum=True), nullable=True)  # Situação mais específica
    
    # Relacionamento com revista RPI
    magazine_id = Column(UUID(as_uuid=True), ForeignKey("rpi_magazine.id"), nullable=True, index=True)
    
    # Relacionamentos
    company = relationship("Company", back_populates="processes")
    alerts = relationship("Alert", back_populates="process")
    magazine = relationship("RPIMagazine", back_populates="processes")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Process(number='{self.process_number}', type='{self.process_type.value}', depositor='{self.depositor}')>" 