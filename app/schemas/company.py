from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class CompanyBase(BaseModel):
    """
    Esquema base para empresas com campos compartilhados.
    """
    name: str = Field(..., min_length=2, max_length=255)
    document: str = Field(..., min_length=11, max_length=20)  # CPF ou CNPJ
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    country: str = Field(default="Brasil", max_length=50)


class CompanyCreate(CompanyBase):
    """
    Esquema para criação de novas empresas.
    """
    user_ids: Optional[List[UUID]] = []  # Lista de UUIDs dos usuários a serem associados


class CompanyUpdate(BaseModel):
    """
    Esquema para atualização de empresas (todos campos opcionais).
    """
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    document: Optional[str] = Field(None, min_length=11, max_length=20)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    country: Optional[str] = Field(None, max_length=50)
    user_ids: Optional[List[UUID]] = None


class CompanyInDB(CompanyBase):
    """
    Esquema para empresas vindas do banco de dados.
    """
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CompanyResponse(CompanyBase):
    """
    Esquema para respostas da API.
    """
    id: UUID
    created_at: datetime
    user_ids: List[UUID] = []  # UUIDs dos usuários associados
    
    class Config:
        from_attributes = True


 