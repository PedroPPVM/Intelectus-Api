from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from app.models.process import ProcessType


class RPIMagazineBase(BaseModel):
    """
    Schema base para revistas RPI - uso interno apenas.
    """
    process_type: ProcessType = Field(..., example=ProcessType.BRAND)
    magazine_identifier: str = Field(..., max_length=255, example="2024_001")
    url: str = Field(..., max_length=1000, example="https://revistas.inpi.gov.br/rpi/rpi_2024_001.pdf")
    publication_date: Optional[date] = Field(None, example="2024-01-15")
    last_checked_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class RPIMagazineCreate(RPIMagazineBase):
    """
    Schema para criação de revistas RPI - uso interno apenas.
    """
    pass


class RPIMagazineUpdate(BaseModel):
    """
    Schema para atualização de revistas RPI - uso interno apenas.
    """
    last_checked_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    publication_date: Optional[date] = None


class RPIMagazineResponse(RPIMagazineBase):
    """
    Schema para resposta de revistas RPI - uso interno apenas.
    """
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

