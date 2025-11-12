from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from enum import Enum

# Re-exportar os enums para uso nos schemas
from app.models.membership import MembershipRole, MembershipPermission


class MembershipRoleEnum(str, Enum):
    """Enum para roles de membership."""
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"
    VIEWER = "viewer"


class MembershipPermissionEnum(str, Enum):
    """Enum para permissões de membership."""
    READ_PROCESSES = "read_processes"
    CREATE_PROCESSES = "create_processes"
    UPDATE_PROCESSES = "update_processes"
    DELETE_PROCESSES = "delete_processes"
    READ_COMPANY_DATA = "read_company_data"
    UPDATE_COMPANY_DATA = "update_company_data"
    MANAGE_USERS = "manage_users"
    VIEW_REPORTS = "view_reports"
    MANAGE_BILLING = "manage_billing"


class MembershipBase(BaseModel):
    """Schema base para membership."""
    user_id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    company_id: UUID = Field(..., example="987fcdeb-51a2-43d1-b123-456789abcdef")
    role: MembershipRoleEnum = Field(default=MembershipRoleEnum.MEMBER, example="member")


class MembershipCreate(MembershipBase):
    """Schema para criação de novo membership."""
    permissions: Optional[List[MembershipPermissionEnum]] = Field(
        default=[], 
        example=["read_processes", "create_processes"],
        description="Lista de permissões específicas para conceder"
    )
    reason: Optional[str] = Field(
        None, 
        max_length=500, 
        example="Novo colaborador adicionado ao projeto",
        description="Motivo da criação do membership"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "role": "admin",
                "permissions": ["read_processes", "create_processes", "update_processes"],
                "reason": "Promovido a administrador da empresa"
            }
        }


class MembershipUpdate(BaseModel):
    """Schema para atualização de membership."""
    role: Optional[MembershipRoleEnum] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[MembershipPermissionEnum]] = Field(
        None,
        description="Nova lista de permissões (substitui as existentes)"
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Motivo da atualização"
    )


class PermissionResponse(BaseModel):
    """Schema para resposta de permissão."""
    permission: MembershipPermissionEnum
    granted_at: datetime
    granted_by_user_id: UUID
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MembershipResponse(MembershipBase):
    """Schema para resposta de membership completo."""
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[UUID] = None
    permissions: List[PermissionResponse] = Field(default=[], description="Permissões específicas concedidas")
    
    # Dados do usuário e empresa para facilitar exibição
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    company_name: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "role": "admin",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T15:45:00Z",
                "created_by_user_id": "456e7890-e89b-12d3-a456-426614174111",
                "permissions": [
                    {
                        "permission": "read_processes",
                        "granted_at": "2024-01-15T10:30:00Z",
                        "granted_by_user_id": "456e7890-e89b-12d3-a456-426614174111",
                        "expires_at": None
                    }
                ],
                "user_name": "João Silva",
                "user_email": "joao@example.com",
                "company_name": "Empresa XYZ Ltda"
            }
        }


class MembershipHistoryResponse(BaseModel):
    """Schema para resposta do histórico de membership."""
    id: UUID
    user_id: UUID
    company_id: UUID
    action: str
    old_role: Optional[MembershipRoleEnum] = None
    new_role: Optional[MembershipRoleEnum] = None
    reason: Optional[str] = None
    performed_by_user_id: UUID
    performed_at: datetime
    ip_address: Optional[str] = None
    
    # Dados para facilitar exibição
    performed_by_name: Optional[str] = None
    user_name: Optional[str] = None
    company_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class MembershipSummary(BaseModel):
    """Schema resumido para listagens."""
    user_id: UUID
    company_id: UUID
    role: MembershipRoleEnum
    is_active: bool
    permissions_count: int = Field(description="Número de permissões específicas")
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    company_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class BulkMembershipCreate(BaseModel):
    """Schema para criação em lote de memberships."""
    company_id: UUID
    memberships: List[MembershipCreate] = Field(..., min_items=1, max_items=50)
    reason: Optional[str] = Field(None, description="Motivo geral para todas as criações")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "reason": "Importação de usuários do sistema antigo",
                "memberships": [
                    {
                        "user_id": "123e4567-e89b-12d3-a456-426614174000",
                        "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                        "role": "member",
                        "permissions": ["read_processes"]
                    },
                    {
                        "user_id": "456e7890-e89b-12d3-a456-426614174111",
                        "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                        "role": "admin",
                        "permissions": ["read_processes", "create_processes", "manage_users"]
                    }
                ]
            }
        }


class MembershipStats(BaseModel):
    """Estatísticas de membership para uma empresa."""
    company_id: UUID
    total_members: int
    active_members: int
    inactive_members: int
    members_by_role: dict = Field(description="Contagem por role")
    recent_changes: int = Field(description="Mudanças nos últimos 7 dias")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "total_members": 15,
                "active_members": 12,
                "inactive_members": 3,
                "members_by_role": {
                    "member": 8,
                    "admin": 3,
                    "owner": 1,
                    "viewer": 3
                },
                "recent_changes": 2
            }
        } 