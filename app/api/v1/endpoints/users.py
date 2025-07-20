from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.security.auth import get_current_user, get_current_superuser
from app.crud import user as crud_user


router = APIRouter()


@router.get("/", response_model=List[UserResponse])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)  # Apenas superusuários
):
    """
    Listar todos os usuários (apenas superusuários).
    """
    users = crud_user.get_multi(db, skip=skip, limit=limit)
    
    # Preparar resposta com company_ids
    response_data = []
    for user in users:
        user_data = UserResponse.model_validate(user)
        user_data.company_ids = [company.id for company in user.companies]
        response_data.append(user_data)
    
    return response_data


@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obter dados de um usuário específico.
    Usuários normais só podem ver seus próprios dados.
    Superusuários podem ver qualquer usuário.
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Verificar permissões
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Preparar resposta
    user_data = UserResponse.model_validate(user)
    user_data.company_ids = [company.id for company in user.companies]
    
    return user_data


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualizar dados de um usuário.
    Usuários normais só podem atualizar seus próprios dados.
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Verificar permissões
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Usuários normais não podem alterar is_superuser
    if not current_user.is_superuser and user_in.is_superuser is not None:
        user_in.is_superuser = None
    
    # Atualizar usuário
    updated_user = crud_user.update(db, db_obj=user, obj_in=user_in)
    
    # Preparar resposta
    user_data = UserResponse.model_validate(updated_user)
    user_data.company_ids = [company.id for company in updated_user.companies]
    
    return user_data


@router.delete("/{user_id}")
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)  # Apenas superusuários
):
    """
    Deletar um usuário (apenas superusuários).
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Não permitir deletar a si mesmo
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar seu próprio usuário"
        )
    
    crud_user.delete(db, id=user_id)
    
    return {"message": "Usuário deletado com sucesso"}


 