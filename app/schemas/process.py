from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum
from uuid import UUID


# Enums alinhados com o modelo planejado
class ProcessTypeEnum(str, Enum):
    """
    Tipos de processos de propriedade intelectual.
    """
    BRAND = "BRAND"
    PATENT = "PATENT"
    DESIGN = "DESIGN"
    SOFTWARE = "SOFTWARE"


class ProcessStatusEnum(str, Enum):
    """
    Status dos processos - situação legal.
    """
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    ABANDONED = "ABANDONED"


class ProcessSituationEnum(str, Enum):
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


class ProcessBase(BaseModel):
    """
    Schema base para processos - alinhado com o modelo planejado.
    """
    process_type: ProcessTypeEnum = Field(..., example=ProcessTypeEnum.BRAND)
    process_number: str = Field(..., min_length=5, max_length=50, example="BR512024123456")
    title: str = Field(..., min_length=5, max_length=1000, example="MARCA EXEMPLO LTDA")
    
    # Depositante/Requerente
    depositor: Optional[str] = Field(None, max_length=500, example="EXEMPLO CONSULTORIA LTDA")
    cnpj_depositor: Optional[str] = Field(None, max_length=20, example="12.345.678/0001-99")
    cpf_depositor: Optional[str] = Field(None, max_length=15, example="123.456.789-00")
    
    # Procurador
    attorney: Optional[str] = Field(None, max_length=500, example="João Silva - OAB/SP 123456")
    
    # Datas importantes  
    deposit_date: Optional[date] = Field(None, example="2024-01-15")
    concession_date: Optional[date] = Field(None, example="2024-06-15")
    validity_date: Optional[date] = Field(None, example="2034-01-15")
    
    # Status e situação
    status: ProcessStatusEnum = Field(default=ProcessStatusEnum.PENDING, example=ProcessStatusEnum.ACTIVE)
    situation: Optional[ProcessSituationEnum] = Field(None, example=ProcessSituationEnum.PUBLISHED)


class ProcessCreate(ProcessBase):
    """
    Schema para criação de novos processos.
    """
    company_id: UUID = Field(..., example="987fcdeb-51a2-43d1-b123-456789abcdef")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "process_type": "BRAND",
                "process_number": "BR512024000001",
                "title": "INTELECTUS CONSULTORIA LTDA",
                "depositor": "INTELECTUS CONSULTORIA LTDA",
                "cnpj_depositor": "12.345.678/0001-99",
                "cpf_depositor": "123.456.789-00",
                "attorney": "João Silva - OAB/SP 123456",
                "deposit_date": "2024-01-15",
                "concession_date": "2024-06-15",
                "validity_date": "2034-01-15",
                "status": "ACTIVE",
                "situation": "PUBLISHED"
            }
        }


class ProcessUpdate(BaseModel):
    """
    Schema para atualização de processos (todos campos opcionais).
    """
    process_type: Optional[ProcessTypeEnum] = None
    process_number: Optional[str] = Field(None, min_length=5, max_length=50)
    title: Optional[str] = Field(None, min_length=5, max_length=1000)
    depositor: Optional[str] = Field(None, max_length=500)
    cnpj_depositor: Optional[str] = Field(None, max_length=20)
    cpf_depositor: Optional[str] = Field(None, max_length=15)
    attorney: Optional[str] = Field(None, max_length=500)
    deposit_date: Optional[date] = None
    concession_date: Optional[date] = None
    validity_date: Optional[date] = None
    status: Optional[ProcessStatusEnum] = None
    situation: Optional[ProcessSituationEnum] = None


class ProcessInDB(ProcessBase):
    """
    Schema para processos vindos do banco de dados.
    """
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProcessResponse(ProcessBase):
    """
    Schema para respostas da API.
    """
    id: UUID = Field(..., example="456e7890-e89b-12d3-a456-426614174111")
    company_id: UUID = Field(..., example="987fcdeb-51a2-43d1-b123-456789abcdef")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "456e7890-e89b-12d3-a456-426614174111",
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "process_type": "BRAND",
                "process_number": "BR512024000001",
                "title": "INTELECTUS CONSULTORIA LTDA",
                "depositor": "INTELECTUS CONSULTORIA LTDA",
                "cnpj_depositor": "12.345.678/0001-99",
                "attorney": "João Silva - OAB/SP 123456",
                "deposit_date": "2024-01-15",
                "concession_date": None,
                "validity_date": "2034-01-15",
                "status": "ACTIVE",
                "situation": "PUBLISHED",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T08:00:00Z"
            }
        }


class ProcessSummary(BaseModel):
    """
    Schema resumido para listagens de processos.
    """
    id: UUID = Field(..., example="456e7890-e89b-12d3-a456-426614174111")
    process_number: str = Field(..., example="BR512024000001")
    attorney: Optional[str] = Field(None, example="João Silva - OAB/SP 123456")
    cpf_depositor: Optional[str] = Field(None, example="123.456.789-00")
    cnpj_depositor: Optional[str] = Field(None, example="12.345.678/0001-99")
    title: str = Field(..., example="INTELECTUS CONSULTORIA LTDA")
    process_type: ProcessTypeEnum = Field(..., example=ProcessTypeEnum.BRAND)
    status: ProcessStatusEnum = Field(..., example=ProcessStatusEnum.ACTIVE)
    situation: Optional[ProcessSituationEnum] = Field(None, example=ProcessSituationEnum.PUBLISHED)
    deposit_date: Optional[date] = Field(None, example="2024-01-15")
    concession_date: Optional[date] = Field(None, example="2024-06-15")
    validity_date: Optional[date] = Field(None, example="2034-01-15")
    depositor: Optional[str] = Field(None, example="INTELECTUS CONSULTORIA LTDA")
    company_id: UUID = Field(..., example="987fcdeb-51a2-43d1-b123-456789abcdef")
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "456e7890-e89b-12d3-a456-726614174111",
                "process_number": "BR512024000001", 
                "attorney": "João Silva - OAB/SP 123456",
                "cpf_depositor": "123.456.789-00",
                "cnpj_depositor": "12.345.678/0001-99",
                "title": "INTELECTUS CONSULTORIA LTDA",
                "process_type": "BRAND",
                "status": "ACTIVE",
                "depositor": "INTELECTUS CONSULTORIA LTDA",
                "deposit_date": "2024-01-15",
                "concession_date": "2024-06-15",
                "validity_date": "2034-01-15",
                "situation": "PUBLISHED",
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "created_at": "2024-01-15T10:30:00Z"
            }
        } 