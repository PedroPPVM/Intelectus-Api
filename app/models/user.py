from sqlalchemy import Column, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base_class import Base


# Tabela de associação para relacionamento N:N entre User e Company
user_company_association = Table(
    'user_company_association',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('user.id'), primary_key=True),
    Column('company_id', UUID(as_uuid=True), ForeignKey('company.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)


class User(Base):
    """
    Modelo para usuários do sistema Intelectus.
    """
    __tablename__ = "user"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Campos de identificação
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    
    # Autenticação
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Relacionamentos N:N com Company (mantido para compatibilidade)
    companies = relationship(
        "Company", 
        secondary=user_company_association, 
        back_populates="users"
    )
    
    # Novo relacionamento com membership avançado
    memberships = relationship("UserCompanyMembership", foreign_keys="UserCompanyMembership.user_id", back_populates="user")
    
    # Relacionamento com alertas
    alerts = relationship("Alert", back_populates="user")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}', full_name='{self.full_name}')>" 