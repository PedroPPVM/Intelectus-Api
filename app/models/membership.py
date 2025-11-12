from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Boolean, Table, ForeignKeyConstraint, TypeDecorator, VARCHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.db.base_class import Base


class MembershipRole(enum.Enum):
    """
    Roles de membership entre User e Company.
    """
    MEMBER = "member"          # Membro básico
    ADMIN = "admin"            # Administrador da empresa
    OWNER = "owner"            # Proprietário da empresa
    VIEWER = "viewer"          # Apenas visualização


class MembershipRoleType(TypeDecorator):
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
        # O valor vem do banco como string ('owner'), precisamos converter para o enum
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


class MembershipPermission(enum.Enum):
    """
    Permissões granulares que podem ser atribuídas.
    """
    READ_PROCESSES = "read_processes"
    CREATE_PROCESSES = "create_processes" 
    UPDATE_PROCESSES = "update_processes"
    DELETE_PROCESSES = "delete_processes"
    READ_COMPANY_DATA = "read_company_data"
    UPDATE_COMPANY_DATA = "update_company_data"
    MANAGE_USERS = "manage_users"
    VIEW_REPORTS = "view_reports"
    MANAGE_BILLING = "manage_billing"


class MembershipPermissionType(TypeDecorator):
    """
    TypeDecorator para garantir que o SQLAlchemy use o valor do enum, não o nome.
    Usa String como impl para evitar problemas com o Enum interno do SQLAlchemy.
    """
    impl = VARCHAR(100)
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
        # O valor vem do banco como string ('read_processes'), precisamos converter para o enum
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


class UserCompanyMembership(Base):
    """
    Tabela principal para relacionamento User ↔ Company com roles.
    Substitui a antiga user_company_association simples.
    """
    __tablename__ = "user_company_membership"
    
    # Chave composta
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), primary_key=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey('company.id'), primary_key=True)
    
    # Informações do membership
    # Usar MembershipRoleType para garantir que o SQLAlchemy use o valor do enum, não o nome
    role = Column(MembershipRoleType(MembershipRole), default=MembershipRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=True)
    
    # Relacionamentos
    user = relationship("User", foreign_keys=[user_id], back_populates="memberships")
    company = relationship("Company", foreign_keys=[company_id], back_populates="memberships")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    permissions = relationship("UserCompanyPermission", back_populates="membership", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Membership(user_id='{self.user_id}', company_id='{self.company_id}', role='{self.role.value}')>"


class MembershipHistory(Base):
    """
    Tabela de auditoria para mudanças de membership.
    """
    __tablename__ = "membership_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Referências do membership
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('company.id'), nullable=False)
    
    # Ação realizada
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, ACTIVATE, DEACTIVATE
    old_role = Column(MembershipRoleType(MembershipRole), nullable=True)
    new_role = Column(MembershipRoleType(MembershipRole), nullable=True)
    reason = Column(Text, nullable=True)
    
    # Metadados de auditoria
    performed_by_user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=False)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv4 ou IPv6
    
    # Relacionamentos
    user = relationship("User", foreign_keys=[user_id])
    company = relationship("Company", foreign_keys=[company_id])
    performed_by = relationship("User", foreign_keys=[performed_by_user_id])
    
    def __repr__(self):
        return f"<MembershipHistory(id='{self.id}', action='{self.action}', performed_at='{self.performed_at}')>"


class UserCompanyPermission(Base):
    """
    Permissões granulares para User ↔ Company.
    """
    __tablename__ = "user_company_permission"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Referências
    user_id = Column(UUID(as_uuid=True), nullable=False)
    company_id = Column(UUID(as_uuid=True), nullable=False)
    permission = Column(MembershipPermissionType(MembershipPermission), nullable=False)
    
    # Metadados
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    granted_by_user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Permissão temporária
    
    # Foreign Key composta para membership
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'company_id'], ['user_company_membership.user_id', 'user_company_membership.company_id']),
    )
    
    # Relacionamentos
    membership = relationship("UserCompanyMembership", back_populates="permissions")
    granted_by = relationship("User", foreign_keys=[granted_by_user_id])
    
    def __repr__(self):
        return f"<Permission(user_id='{self.user_id}', company_id='{self.company_id}', permission='{self.permission.value}')>" 