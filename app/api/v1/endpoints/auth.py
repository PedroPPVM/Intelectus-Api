from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.user import UserLogin, UserResponse, UserCreate, UserUpdate
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.config import settings
from app.db.session import get_db
from app.security.auth import (
    Token, authenticate_user, create_access_token, get_current_user
)
from app.services.user_service import user_service
from app.models.user import User


router = APIRouter()


@router.post("/login", response_model=Token, summary="Login do Usuário", description="Autenticação simples com email e senha")
def login_access_token(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    **Login simplificado** - apenas email e senha necessários.
    
    Retorna um token JWT válido por 30 minutos para usar nos outros endpoints.
    """
    user = user_service.authenticate_user_credentials(
        db=db,
        email=user_credentials.email,
        password=user_credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo"
        )
    
    # Criar token de acesso
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60  # em segundos
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate
):
    """
    Registrar um novo usuário.
    """
    return user_service.create_user(db=db, user_create=user_in)


@router.get("/me", response_model=UserResponse)
def read_users_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obter dados do usuário atual.
    """
    return user_service.get_user_by_id(db=db, user_id=current_user.id)


@router.post("/test-token", response_model=UserResponse)
def test_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Testar se o token é válido retornando os dados do usuário.
    """
    return user_service.get_user_by_id(db=db, user_id=current_user.id) 


@router.post("/promote-to-superuser/{user_id}", response_model=UserResponse)
def promote_to_superuser(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Promover usuário a Super User** - apenas super users podem fazer isso.
    
    Super users têm acesso a endpoints administrativos e podem:
    - Promover outros usuários
    - Acessar dados de todas as empresas
    - Gerenciar sistema como um todo
    """
    # Verificar se o usuário atual é super user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas super usuários podem promover outros usuários"
        )
    
    return user_service.promote_to_superuser(
        db=db, 
        user_id=user_id, 
        promoted_by_user_id=current_user.id
    )


@router.post("/login-oauth", response_model=Token, summary="Login OAuth2 (Compatibilidade)")
def login_oauth_compatible(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    **Login compatível com OAuth2** (para sistemas que precisam dos campos extras).
    
    Use este endpoint se você precisar de compatibilidade com OAuth2.
    Para uso normal, prefira o endpoint `/login` mais simples.
    """
    user = user_service.authenticate_user_credentials(
        db=db, 
        email=form_data.username, 
        password=form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo"
        )
    
    # Criar token de acesso
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }


@router.post("/create-first-superuser", response_model=UserResponse)
def create_first_superuser(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """
    **Criar primeiro Super User** do sistema (apenas se não existir nenhum).
    
    Este endpoint só funciona se não houver nenhum super user no sistema.
    É útil para setup inicial da aplicação.
    """
    return user_service.create_first_superuser(db=db, user_create=user_create) 


@router.get("/superuser-info", summary="Informações de Super Users")
def get_superuser_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Verificar informações sobre super users** no sistema.
    
    Mostra quantos super users existem e se você é um deles.
    Útil para debugging e setup inicial.
    """
    # Obter estatísticas dos superusers via service
    stats = user_service.get_superuser_stats(db)
    
    return {
        "your_info": {
            "id": str(current_user.id),
            "email": current_user.email,
            "is_superuser": current_user.is_superuser,
            "is_active": current_user.is_active
        },
        "system_info": {
            "total_superusers": stats["total_superusers"],
            "superuser_emails": stats["superuser_emails"],
            "can_create_first_superuser": stats["can_create_first_superuser"],
            "can_promote_users": current_user.is_superuser
        },
        "instructions": {
            "to_become_superuser": "Se você não é super user, peça para um super user existente te promover via POST /promote-to-superuser/{seu-id}",
            "to_create_first": "Se não existir nenhum super user, use POST /create-first-superuser",
            "current_status": "Super User" if current_user.is_superuser else "Usuário Normal"
        }
    } 