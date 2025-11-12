from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.security.auth import get_current_user, get_current_superuser
from app.services.company_service import company_service
from app.services.access_control_service import access_control_service


router = APIRouter()


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    *,
    db: Session = Depends(get_db),
    company_in: CompanyCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Criar uma nova empresa - REFATORADO COM SERVICES.
    
    Usa CompanyService para centralizar todas as validações.
    """
    # Usar CompanyService com todas as validações
    company = company_service.create_company_with_validation(
        db, company_in, current_user
    )
    
    # Usar CompanyService para transformação padronizada
    response_data = company_service.transform_to_company_response(company)
    
    return response_data


@router.get("/", response_model=List[CompanyResponse])
def read_companies(
    skip: int = 0,
    limit: int = 100,
    name: str = Query(None, description="Filtrar por nome da empresa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar empresas - REFATORADO COM SERVICES.
    
    Usa CompanyService para centralizar lógicas de acesso e filtros.
    """
    # Usar CompanyService com filtros centralizados
    filters = {
        'skip': skip,
        'limit': limit,
        'name': name
    }
    
    companies = company_service.get_user_companies_with_filters(
        db, current_user, filters
    )
    
    # Usar CompanyService para transformação em lote
    response_data = company_service.transform_to_company_response_list(companies)
    
    return response_data


@router.get("/{company_id}", response_model=CompanyResponse)
def read_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obter dados de uma empresa específica - REFATORADO COM SERVICES.
    
    Usa AccessControlService + CompanyService para validação e transformação.
    """
    # Usar AccessControlService para validação centralizada
    company = access_control_service.validate_company_access(
        db, current_user, company_id, "read_company_data"
    )
    
    # Usar CompanyService para transformação padronizada
    response_data = company_service.transform_to_company_response(company)
    
    return response_data


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: UUID,
    company_in: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualizar dados de uma empresa - REFATORADO COM SERVICES.
    
    Usa CompanyService para centralizar todas as validações e transformações.
    """
    # Usar CompanyService com todas as validações
    updated_company = company_service.update_company_with_validation(
        db, company_id, company_in, current_user
    )
    
    # Usar CompanyService para transformação padronizada
    response_data = company_service.transform_to_company_response(updated_company)
    
    return response_data


@router.delete("/{company_id}")
def delete_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)  # Apenas superusuários
):
    """
    Deletar uma empresa - REFATORADO COM SERVICES.
    
    Usa CompanyService para centralizar validações de integridade.
    """
    # Usar CompanyService com todas as validações de integridade
    company_service.delete_company_with_validation(
        db, company_id, current_user
    )
    
    return {"message": "Empresa deletada com sucesso"}


 