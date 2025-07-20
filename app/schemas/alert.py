from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID


class AlertTypeEnum(str, Enum):
    """
    Tipos de alertas do sistema.
    """
    STATUS_CHANGE = "mudanca_status"
    PUBLICATION = "publicacao"
    DEADLINE = "prazo"
    SIMILAR_PROCESS = "processo_similar"
    RENEWAL_DUE = "renovacao_vencimento"


class AlertBase(BaseModel):
    """
    Esquema base para alertas com campos compartilhados.
    """
    title: str = Field(..., min_length=5, max_length=500)
    message: str = Field(..., min_length=10)
    alert_type: AlertTypeEnum
    is_read: bool = False
    is_dismissed: bool = False


class AlertCreate(BaseModel):
    """
    Esquema para criação de novos alertas.
    """
    title: str = Field(..., min_length=5, max_length=500)
    message: str = Field(..., min_length=10)
    alert_type: AlertTypeEnum
    user_id: UUID
    process_id: Optional[UUID] = None


class AlertUpdate(BaseModel):
    """
    Esquema para atualização de alertas.
    """
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class AlertInDB(AlertBase):
    """
    Esquema para alertas vindos do banco de dados.
    """
    id: UUID
    user_id: UUID
    process_id: Optional[UUID] = None
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AlertResponse(AlertBase):
    """
    Esquema para respostas da API.
    """
    id: UUID
    user_id: UUID
    process_id: Optional[UUID] = None
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 