from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.security.auth import get_current_user, get_current_superuser
from app.services.user_service import user_service


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
    
    REFATORADO: Usa UserService para transformação padronizada.
    """
    from app.crud import user as crud_user
    users = crud_user.get_multi(db, skip=skip, limit=limit)
    
    # Usar UserService para transformação padronizada
    response_data = []
    for user in users:
        user_response = user_service.get_user_by_id(db, user.id)
        response_data.append(user_response)
    
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
    
    REFATORADO: Usa UserService para validação e transformação padronizada.
    """
    # Verificar permissões
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Usar UserService para validação e transformação padronizada
    return user_service.get_user_by_id(db, user_id)


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
    
    REFATORADO: Usa UserService para validação e transformação padronizada.
    """
    # Verificar permissões
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Usuários normais não podem alterar is_superuser
    if not current_user.is_superuser and user_in.is_superuser is not None:
        user_in.is_superuser = None
    
    # REFATORADO: Usar UserService para atualização e transformação padronizada
    # O UserService já valida se o usuário existe
    return user_service.update_user(
        db=db,
        user_id=user_id,
        user_update=user_in,
        updated_by_user_id=current_user.id
    )


@router.delete("/{user_id}")
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)  # Apenas superusuários
):
    """
    Deletar um usuário (apenas superusuários).
    
    REFATORADO: Usa UserService para validação e exclusão padronizada.
    """
    # Não permitir deletar a si mesmo
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar seu próprio usuário"
        )
    
    # REFATORADO: Usar UserService para exclusão padronizada
    # O UserService já valida se o usuário existe
    user_service.delete_user(
        db=db,
        user_id=user_id,
        deleted_by_user_id=current_user.id
    )
    
    return {"message": "Usuário deletado com sucesso"}


 