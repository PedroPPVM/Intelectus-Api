from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum
from uuid import UUID


# Enums para uso nos esquemas
class ProcessTypeEnum(str, Enum):
    """
    Tipos de processos de propriedade intelectual.
    """
    BRAND = "marca"
    PATENT = "patente"
    DESIGN = "desenho_industrial"
    SOFTWARE = "programa_computador"
    UTILITY_MODEL = "modelo_utilidade"


class ProcessStatusEnum(str, Enum):
    """
    Status dos processos.
    """
    PENDING = "pendente"
    ACTIVE = "ativo"
    GRANTED = "deferido"
    DENIED = "indeferido"
    EXPIRED = "expirado"
    ABANDONED = "abandonado"


class ProcessBase(BaseModel):
    """
    Esquema base para processos com campos compartilhados.
    """
    process_number: str = Field(..., min_length=5, max_length=20, example="BR512024123456")
    title: str = Field(..., min_length=5, max_length=500, example="Sistema de Gestão Inteligente de Propriedade Intelectual")
    short_title: Optional[str] = Field(None, max_length=100, description="Abreviação do título para exibição", example="Sistema Gestão PI")
    description: Optional[str] = Field(None, example="Sistema completo para monitoramento automático de processos de PI no INPI")
    process_type: ProcessTypeEnum = Field(..., example=ProcessTypeEnum.SOFTWARE)
    status: ProcessStatusEnum = Field(default=ProcessStatusEnum.PENDING, example=ProcessStatusEnum.ACTIVE)
    filing_date: Optional[date] = Field(None, example="2024-01-15")
    publication_date: Optional[date] = Field(None, example="2024-02-15")
    grant_date: Optional[date] = Field(None, example=None)
    expiry_date: Optional[date] = Field(None, example="2034-01-15")
    applicant_name: Optional[str] = Field(None, max_length=500, example="Intelectus Consultoria LTDA")
    applicant_document: Optional[str] = Field(None, max_length=20, example="12.345.678/0001-99")
    nice_classification: Optional[str] = Field(None, max_length=100, example="42")
    ipc_classification: Optional[str] = Field(None, max_length=100, example="G06F 17/30")


class ProcessCreate(ProcessBase):
    """
    Esquema para criação de novos processos.
    """
    company_id: UUID = Field(..., example="987fcdeb-51a2-43d1-b123-456789abcdef")
    
    class Config:
        json_schema_extra = {
            "example": {
                "process_number": "BR512024000001",
                "title": "Marca INTELECTUS para Serviços de Consultoria em PI",
                "short_title": "INTELECTUS - Consultoria PI",
                "description": "Marca destinada a identificar serviços de consultoria em propriedade intelectual",
                "process_type": "marca",
                "status": "ativo",
                "filing_date": "2024-01-15",
                "applicant_name": "Intelectus Consultoria LTDA",
                "applicant_document": "12.345.678/0001-99",
                "nice_classification": "35, 42",
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef"
            }
        }


class ProcessUpdate(BaseModel):
    """
    Esquema para atualização de processos (todos campos opcionais).
    """
    process_number: Optional[str] = Field(None, min_length=5, max_length=20)
    title: Optional[str] = Field(None, min_length=5, max_length=500)
    short_title: Optional[str] = Field(None, max_length=100, description="Abreviação do título para exibição")
    description: Optional[str] = None
    process_type: Optional[ProcessTypeEnum] = None
    status: Optional[ProcessStatusEnum] = None
    filing_date: Optional[date] = None
    publication_date: Optional[date] = None
    grant_date: Optional[date] = None
    expiry_date: Optional[date] = None
    applicant_name: Optional[str] = Field(None, max_length=500)
    applicant_document: Optional[str] = Field(None, max_length=20)
    nice_classification: Optional[str] = Field(None, max_length=100)
    ipc_classification: Optional[str] = Field(None, max_length=100)


class ProcessInDB(ProcessBase):
    """
    Esquema para processos vindos do banco de dados.
    """
    id: UUID
    company_id: UUID
    last_scraped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProcessResponse(ProcessBase):
    """
    Esquema para respostas da API.
    """
    id: UUID = Field(..., example="456e7890-e89b-12d3-a456-426614174111")
    company_id: UUID = Field(..., example="987fcdeb-51a2-43d1-b123-456789abcdef")
    created_at: datetime
    last_scraped_at: Optional[datetime] = Field(None, description="Última vez que este processo foi verificado via scraping")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "456e7890-e89b-12d3-a456-426614174111",
                "process_number": "BR512024000001",
                "title": "Sistema de Gestão Inteligente de Propriedade Intelectual",
                "short_title": "Sistema Gestão PI",
                "description": "Sistema completo para monitoramento de processos de PI",
                "process_type": "programa_computador",
                "status": "ativo",
                "filing_date": "2024-01-15",
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "created_at": "2024-01-15T10:30:00Z",
                "last_scraped_at": "2024-01-20T08:00:00Z"
            }
        }


class ProcessSummary(BaseModel):
    """
    Esquema resumido para listagens de processos (usando short_title preferencialmente).
    """
    id: UUID = Field(..., example="456e7890-e89b-12d3-a456-426614174111")
    process_number: str = Field(..., example="BR512024000001")
    display_title: str = Field(..., description="short_title se disponível, senão título truncado", example="Sistema Gestão PI")
    process_type: ProcessTypeEnum = Field(..., example=ProcessTypeEnum.SOFTWARE)
    status: ProcessStatusEnum = Field(..., example=ProcessStatusEnum.ACTIVE)
    company_id: UUID = Field(..., example="987fcdeb-51a2-43d1-b123-456789abcdef")
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "456e7890-e89b-12d3-a456-726614174111",
                "process_number": "BR512024000001",
                "display_title": "Sistema Gestão PI",
                "process_type": "programa_computador",
                "status": "ativo",
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "created_at": "2024-01-15T10:30:00Z"
            }
        } 