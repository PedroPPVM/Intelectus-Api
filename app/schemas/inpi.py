from pydantic import BaseModel, Field
from typing import Optional


class MarcaLookupResponse(BaseModel):
    """
    Schema de resposta para consulta de marca no portal pePI do INPI.
    """
    process_number: str = Field(..., description="Número do processo consultado", example="942926668")
    marca: Optional[str] = Field(None, description="Nome da marca registrada", example="REQUEMILHO")
    situacao: Optional[str] = Field(None, description="Situação atual do processo", example="Aguardando prazo de apresentação de oposição")

    class Config:
        json_schema_extra = {
            "example": {
                "process_number": "942926668",
                "marca": "REQUEMILHO",
                "situacao": "Aguardando prazo de apresentação de oposição"
            }
        }
