from sqlalchemy import Column, String, Date, Enum, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.db.base_class import Base
from app.models.process import ProcessType


class RPIMagazine(Base):
    """
    Modelo para controle de versões de revistas RPI.
    
    Armazena informações sobre as revistas RPI baixadas e processadas,
    permitindo rastrear qual revista foi usada para atualizar cada processo.
    """
    __tablename__ = "rpi_magazine"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Tipo de processo da revista
    process_type = Column(Enum(ProcessType, name="processtype", native_enum=True), nullable=False, index=True)
    
    # Identificador único da revista (extraído da URL/nome do arquivo)
    # Usado para comparar rapidamente se já temos essa revista
    magazine_identifier = Column(String(255), nullable=False, index=True)
    
    # URL completa da revista
    url = Column(String(1000), nullable=False)
    
    # Data de publicação da revista (extraída do HTML se disponível)
    publication_date = Column(Date, nullable=True)
    
    # Data da última verificação (quando foi checada no site)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Data do último processamento (quando foi usada para atualizar processos)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamento com processos
    processes = relationship("Process", back_populates="magazine")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Índice composto para busca rápida por tipo e identificador
    __table_args__ = (
        Index('ix_rpi_magazine_type_identifier', 'process_type', 'magazine_identifier'),
    )
    
    def __repr__(self):
        return f"<RPIMagazine(id='{self.id}', type='{self.process_type.value}', identifier='{self.magazine_identifier}')>"

