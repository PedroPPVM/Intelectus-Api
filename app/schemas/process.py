from pydantic import BaseModel, Field
from typing import Optional, Dict
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
    status: str = Field(default="PENDING", example="ativo")
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
                "status": "ativo",
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
    status: Optional[str] = None
    situation: Optional[ProcessSituationEnum] = None
    magazine_id: Optional[UUID] = None


class ProcessInDB(ProcessBase):
    """
    Schema para processos vindos do banco de dados.
    """
    id: UUID
    company_id: UUID
    magazine_id: Optional[UUID] = None
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
    magazine_id: Optional[UUID] = Field(None, example="789e1234-e89b-12d3-a456-426614174222")
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
                "status": "ativo",
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
    status: str = Field(..., example="ativo")
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
                "status": "ativo",
                "depositor": "INTELECTUS CONSULTORIA LTDA",
                "deposit_date": "2024-01-15",
                "concession_date": "2024-06-15",
                "validity_date": "2034-01-15",
                "situation": "PUBLISHED",
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class ProcessUpdateByTypeResult(BaseModel):
    """
    Schema para resultado de atualização por tipo de processo.
    """
    process_type: str = Field(..., example="BRAND", description="Tipo de processo")
    total: int = Field(..., example=10, description="Total de processos desse tipo")
    updated: int = Field(..., example=3, description="Quantos processos foram atualizados")
    magazine_created: bool = Field(False, example=False, description="Se uma nova revista foi criada")
    magazine_identifier: Optional[str] = Field(None, example="2024_001", description="Identificador da revista usada")
    skipped: Optional[bool] = Field(None, example=False, description="Se o processamento foi pulado (otimização)")
    message: Optional[str] = Field(None, example="Revista já processada e todos os processos já estão atualizados", description="Mensagem informativa")
    error: Optional[str] = Field(None, example=None, description="Mensagem de erro se houver")


class ProcessUpdateFromMagazinesResponse(BaseModel):
    """
    Schema para resposta da atualização de processos a partir de revistas RPI.
    """
    company_id: str = Field(..., example="987fcdeb-51a2-43d1-b123-456789abcdef", description="ID da empresa")
    process_type: str = Field(..., example="BRAND", description="Tipo de processo atualizado ou 'ALL' se todos")
    total_processes: int = Field(..., example=10, description="Total de processos verificados")
    updated_processes: int = Field(..., example=3, description="Total de processos atualizados")
    new_magazines: int = Field(..., example=1, description="Quantas novas revistas foram baixadas")
    by_type: Dict[str, ProcessUpdateByTypeResult] = Field(..., description="Detalhes por tipo de processo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
                "process_type": "BRAND",
                "total_processes": 10,
                "updated_processes": 3,
                "new_magazines": 1,
                "by_type": {
                    "BRAND": {
                        "process_type": "BRAND",
                        "total": 10,
                        "updated": 3,
                        "magazine_created": True,
                        "magazine_identifier": "2024_001",
                        "skipped": False,
                        "message": None,
                        "error": None
                    }
                }
            }
        } 