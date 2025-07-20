from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base_class import Base
from app.models.user import user_company_association


class Company(Base):
    """
    Modelo para empresas/organizações no sistema Intelectus.
    """
    __tablename__ = "company"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Informações da empresa
    name = Column(String(255), nullable=False, index=True)
    document = Column(String(20), unique=True, nullable=False)  # CNPJ ou CPF
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Endereço
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    country = Column(String(50), default="Brasil")
    
    # Relacionamentos N:N com User (mantido para compatibilidade)
    users = relationship(
        "User", 
        secondary=user_company_association, 
        back_populates="companies"
    )
    
    # Novo relacionamento com membership avançado
    memberships = relationship("UserCompanyMembership", foreign_keys="UserCompanyMembership.company_id", back_populates="company")
    
    # Relacionamento 1:N com Process
    processes = relationship("Process", back_populates="company")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Company(id='{self.id}', name='{self.name}', document='{self.document}')>" 