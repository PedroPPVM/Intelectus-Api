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


class PatenteLookupResponse(BaseModel):
    """
    Schema de resposta para consulta de patente no portal pePI do INPI.

    O campo `title` corresponde ao "Título" extraído da página de detalhe
    e é compatível com o campo `title` do schema Process.
    """
    process_number: str = Field(..., description="Número do processo consultado", example="BR 10 2023 002986")
    title: Optional[str] = Field(None, description="Título da patente", example="MÉTODO DE EXTRAÇÃO E REAPROVEITAMENTO DO AMIDO DA BIOMASSA DE BAMBU NA INDÚSTRIA PRODUTORA DE POLPA CELULÓSICA E PAPEL")

    class Config:
        json_schema_extra = {
            "example": {
                "process_number": "BR 10 2023 002986",
                "title": "MÉTODO DE EXTRAÇÃO E REAPROVEITAMENTO DO AMIDO DA BIOMASSA DE BAMBU NA INDÚSTRIA PRODUTORA DE POLPA CELULÓSICA E PAPEL"
            }
        }
