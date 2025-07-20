from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.models.user import User
from app.models.company import Company
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserLogin
)
from app.crud import user as crud_user
from app.security.auth import authenticate_user, create_password_hash


class UserService:
    """
    Service para gerenciar usuários com regras de negócio e validações.
    
    Responsabilidades:
    - Criar/atualizar/deletar usuários
    - Gerenciar superusers
    - Autenticação e autorização
    - Validar regras de negócio
    - Fornecer consultas otimizadas
    """
    
    def create_first_superuser(
        self,
        db: Session,
        *,
        user_create: UserCreate
    ) -> UserResponse:
        """
        Criar primeiro Super User do sistema (apenas se não existir nenhum).
        
        Este método só funciona se não houver nenhum super user no sistema.
        É útil para setup inicial da aplicação.
        """
        # Verificar se já existe algum super user
        existing_superuser = crud_user.get_first_superuser(db)
        if existing_superuser:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe pelo menos um super usuário no sistema"
            )
        
        # Verificar se email já existe
        existing_user = crud_user.get_by_email(db, email=user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já está em uso"
            )
        
        # Criar usuário como super user
        superuser_data = UserCreate(
            email=user_create.email,
            full_name=user_create.full_name,
            password=user_create.password,
            is_superuser=True,
            company_ids=user_create.company_ids or []
        )
        
        user = crud_user.create(db=db, obj_in=superuser_data)
        
        return self._build_user_response(db, user)
    
    def create_user(
        self,
        db: Session,
        *,
        user_create: UserCreate,
        created_by_user_id: Optional[UUID] = None
    ) -> UserResponse:
        """
        Criar novo usuário com validações de negócio.
        """
        # Verificar se email já existe
        existing_user = crud_user.get_by_email(db, email=user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já está em uso"
            )
        
        # Validar empresas se fornecidas
        if user_create.company_ids:
            companies = db.query(Company).filter(
                Company.id.in_(user_create.company_ids)
            ).all()
            
            if len(companies) != len(user_create.company_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uma ou mais empresas não foram encontradas"
                )
        
        user = crud_user.create(db=db, obj_in=user_create)
        
        return self._build_user_response(db, user)
    
    def get_user_by_id(
        self,
        db: Session,
        user_id: UUID
    ) -> UserResponse:
        """
        Buscar usuário por ID com informações completas.
        """
        user = crud_user.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        return self._build_user_response(db, user)
    
    def get_user_by_email(
        self,
        db: Session,
        email: str
    ) -> Optional[UserResponse]:
        """
        Buscar usuário por email.
        """
        user = crud_user.get_by_email(db, email=email)
        if not user:
            return None
        
        return self._build_user_response(db, user)
    
    def update_user(
        self,
        db: Session,
        *,
        user_id: UUID,
        user_update: UserUpdate,
        updated_by_user_id: Optional[UUID] = None
    ) -> UserResponse:
        """
        Atualizar usuário existente com validações.
        """
        user = crud_user.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        # Verificar se email já está em uso por outro usuário
        if user_update.email and user_update.email != user.email:
            existing_user = crud_user.get_by_email(db, email=user_update.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email já está em uso por outro usuário"
                )
        
        # Validar empresas se fornecidas
        if user_update.company_ids is not None:
            companies = db.query(Company).filter(
                Company.id.in_(user_update.company_ids)
            ).all()
            
            if len(companies) != len(user_update.company_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uma ou mais empresas não foram encontradas"
                )
        
        updated_user = crud_user.update(db=db, db_obj=user, obj_in=user_update)
        
        return self._build_user_response(db, updated_user)
    
    def delete_user(
        self,
        db: Session,
        *,
        user_id: UUID,
        deleted_by_user_id: Optional[UUID] = None
    ) -> bool:
        """
        Deletar usuário (soft delete - desativar).
        """
        user = crud_user.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        # Desativar ao invés de deletar fisicamente
        user_update = UserUpdate(is_active=False)
        crud_user.update(db=db, db_obj=user, obj_in=user_update)
        
        return True
    
    def promote_to_superuser(
        self,
        db: Session,
        *,
        user_id: UUID,
        promoted_by_user_id: UUID
    ) -> UserResponse:
        """
        Promover usuário a superuser.
        """
        user = crud_user.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        if user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário já é um superuser"
            )
        
        user_update = UserUpdate(is_superuser=True)
        updated_user = crud_user.update(db=db, db_obj=user, obj_in=user_update)
        
        return self._build_user_response(db, updated_user)
    
    def get_superuser_stats(
        self,
        db: Session
    ) -> Dict[str, Any]:
        """
        Obter estatísticas sobre superusers no sistema.
        """
        superusers = db.query(User).filter(User.is_superuser == True).all()
        
        return {
            "total_superusers": len(superusers),
            "superuser_emails": [u.email for u in superusers],
            "can_create_first_superuser": len(superusers) == 0
        }
    
    def authenticate_user_credentials(
        self,
        db: Session,
        *,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Autenticar usuário com email e senha.
        """
        user = authenticate_user(db, email=email, password=password)
        return user
    
    def _build_user_response(
        self,
        db: Session,
        user: User
    ) -> UserResponse:
        """
        Construir resposta completa de usuário com informações das empresas.
        """
        # Buscar IDs das empresas associadas
        company_ids = [company.id for company in user.companies]
        
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            company_ids=company_ids
        )


# Instância singleton do service
user_service = UserService() 