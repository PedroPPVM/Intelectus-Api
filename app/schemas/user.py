from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Esquemas base
class UserBase(BaseModel):
    """
    Esquema base para usuários com campos compartilhados.
    """
    email: EmailStr = Field(..., example="usuario@intelectus.com.br")
    full_name: str = Field(..., min_length=2, max_length=255, example="João Silva")
    is_active: bool = Field(default=True, example=True)
    is_superuser: bool = Field(default=False, example=False)


class UserCreate(BaseModel):
    """
    Esquema para criação de novos usuários.
    """
    email: EmailStr = Field(..., example="novo.usuario@intelectus.com.br")
    full_name: str = Field(..., min_length=2, max_length=255, example="Maria Santos")
    password: str = Field(..., min_length=6, example="senhaSegura123")
    is_superuser: Optional[bool] = Field(default=False, example=False, description="Se o usuário deve ser criado como superuser")
    company_ids: Optional[List[UUID]] = Field(default=[], example=[], description="Lista de UUIDs das empresas a serem associadas")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "advogado@escritorio.com.br",
                "full_name": "Dr. Carlos Pereira",
                "password": "minhasenha123",
                "is_superuser": False,
                "company_ids": []
            }
        }


class UserUpdate(BaseModel):
    """
    Esquema para atualização de usuários (todos campos opcionais).
    """
    email: Optional[EmailStr] = Field(None, example="email.atualizado@intelectus.com.br")
    full_name: Optional[str] = Field(None, min_length=2, max_length=255, example="Nome Atualizado")
    password: Optional[str] = Field(None, min_length=6, example="novaSenha456")
    is_active: Optional[bool] = Field(None, example=True)
    is_superuser: Optional[bool] = Field(None, example=False)
    company_ids: Optional[List[UUID]] = Field(None, description="Atualizar empresas associadas")


class UserInDB(UserBase):
    """
    Esquema para usuários vindos do banco de dados.
    """
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Para SQLAlchemy 2.0+


class UserResponse(UserBase):
    """
    Esquema para respostas da API (sem dados sensíveis).
    """
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    created_at: datetime
    company_ids: List[UUID] = Field(default=[], example=["987fcdeb-51a2-43d1-b123-456789abcdef"], description="UUIDs das empresas associadas")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "usuario@intelectus.com.br",
                "full_name": "João Silva",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2024-01-15T10:30:00Z",
                "company_ids": ["987fcdeb-51a2-43d1-b123-456789abcdef"]
            }
        }


class UserLogin(BaseModel):
    """
    Esquema para login de usuários.
    """
    email: EmailStr = Field(..., example="admin@intelectus.com.br")
    password: str = Field(..., example="senha123")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@intelectus.com.br", 
                "password": "senha123"
            }
        }


 