import logging
from fastapi import APIRouter, Depends, HTTPException, status, Path
from requests.exceptions import ConnectionError, Timeout, HTTPError

from app.models.user import User
from app.schemas.inpi import MarcaLookupResponse, PatenteLookupResponse, ProgramaLookupResponse
from app.security.auth import get_current_user
from app.services.inpi_pepi_service import inpi_pepi_service

logger = logging.getLogger('intelectus.endpoints.inpi')

router = APIRouter()


@router.get(
    "/marca/{process_number}",
    response_model=MarcaLookupResponse,
    summary="Consultar marca no INPI pePI",
    description="Consulta informações de uma marca no portal pePI do INPI pelo número do processo.",
)
def lookup_marca(
    process_number: str = Path(
        ...,
        min_length=5,
        max_length=20,
        description="Número do processo de marca no INPI",
        example="942926668",
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Consultar dados de marca no portal pePI do INPI.

    Retorna o nome da marca e a situação atual do processo.
    """
    try:
        result = inpi_pepi_service.lookup_marca(process_number)
        return MarcaLookupResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except (ConnectionError, Timeout) as e:
        logger.error(f"❌ Erro de conexão com INPI pePI: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar ao portal INPI pePI. Tente novamente mais tarde.",
        )
    except HTTPError as e:
        logger.error(f"❌ Erro HTTP do INPI pePI: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O portal INPI pePI retornou um erro. Tente novamente mais tarde.",
        )
    except Exception as e:
        logger.error(f"❌ Erro inesperado na consulta pePI: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar o INPI pePI.",
        )


@router.get(
    "/patente/{process_number:path}",
    response_model=PatenteLookupResponse,
    summary="Consultar patente no INPI pePI",
    description=(
        "Consulta o título de uma patente no portal pePI do INPI pelo número do pedido. "
        "Aceita o número no formato com espaços (ex: `BR 10 2023 002986`). "
        "O campo `title` retornado é compatível com o campo `title` do schema Process."
    ),
)
def lookup_patente(
    process_number: str = Path(
        ...,
        min_length=5,
        max_length=40,
        description="Número do pedido de patente (ex: 'BR 10 2023 002986')",
        example="BR 10 2023 002986",
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Consultar dados de patente no portal pePI do INPI.

    Retorna o título da patente extraído da página de detalhe.
    """
    try:
        result = inpi_pepi_service.lookup_patente(process_number)
        return PatenteLookupResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except (ConnectionError, Timeout) as e:
        logger.error(f"❌ Erro de conexão com INPI pePI (patente): {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar ao portal INPI pePI. Tente novamente mais tarde.",
        )
    except HTTPError as e:
        logger.error(f"❌ Erro HTTP do INPI pePI (patente): {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O portal INPI pePI retornou um erro. Tente novamente mais tarde.",
        )
    except Exception as e:
        logger.error(f"❌ Erro inesperado na consulta pePI (patente): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar o INPI pePI.",
        )


@router.get(
    "/programa/{process_number:path}",
    response_model=ProgramaLookupResponse,
    summary="Consultar programa de computador no INPI pePI",
    description=(
        "Consulta o título de um programa de computador no portal pePI do INPI pelo número do pedido. "
        "Aceita o número no formato com espaços e hífen (ex: `BR 51 2026 002418-8`). "
        "O campo `title` retornado é compatível com o campo `title` do schema Process."
    ),
)
def lookup_programa(
    process_number: str = Path(
        ...,
        min_length=5,
        max_length=40,
        description="Número do pedido de programa de computador (ex: 'BR 51 2026 002418-8')",
        example="BR 51 2026 002418-8",
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Consultar dados de programa de computador no portal pePI do INPI.

    Retorna o título do programa extraído da página de detalhe.
    """
    try:
        result = inpi_pepi_service.lookup_programa(process_number)
        return ProgramaLookupResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except (ConnectionError, Timeout) as e:
        logger.error(f"❌ Erro de conexão com INPI pePI (programa): {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar ao portal INPI pePI. Tente novamente mais tarde.",
        )
    except HTTPError as e:
        logger.error(f"❌ Erro HTTP do INPI pePI (programa): {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O portal INPI pePI retornou um erro. Tente novamente mais tarde.",
        )
    except Exception as e:
        logger.error(f"❌ Erro inesperado na consulta pePI (programa): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar o INPI pePI.",
        )
