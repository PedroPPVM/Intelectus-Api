from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.user import User
from app.models.company import Company
from app.schemas.user import UserCreate, UserUpdate
from app.security.auth import create_password_hash


class CRUDUser:
    """
    Operações CRUD para o modelo User.
    """
    
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """
        Criar um novo usuário.
        """
        # Hash da senha
        hashed_password = create_password_hash(obj_in.password)
        
        # Criar usuário
        db_user = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=obj_in.is_superuser or False
        )
        
        db.add(db_user)
        db.flush()  # Para obter o ID
        
        # Associar com empresas se fornecidas
        if obj_in.company_ids:
            companies = db.query(Company).filter(Company.id.in_(obj_in.company_ids)).all()
            db_user.companies.extend(companies)
        
        db.commit()
        db.refresh(db_user)
        return db_user
    
    def get(self, db: Session, id: UUID) -> Optional[User]:
        """
        Buscar usuário por ID.
        """
        return db.query(User).filter(User.id == id).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """
        Buscar usuário por email.
        """
        return db.query(User).filter(User.email == email).first()
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """
        Buscar múltiplos usuários com paginação.
        """
        return db.query(User).offset(skip).limit(limit).all()
    
    def update(
        self, db: Session, *, db_obj: User, obj_in: UserUpdate
    ) -> User:
        """
        Atualizar um usuário existente.
        """
        update_data = obj_in.dict(exclude_unset=True)
        
        # Se senha foi fornecida, fazer hash
        if "password" in update_data:
            hashed_password = create_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        
        # Atualizar relacionamentos com empresas
        if "company_ids" in update_data:
            company_ids = update_data.pop("company_ids")
            if company_ids is not None:
                companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
                db_obj.companies = companies
        
        # Atualizar demais campos
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: UUID) -> Optional[User]:
        """
        Deletar um usuário.
        """
        obj = db.query(User).filter(User.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def is_active(self, user: User) -> bool:
        """
        Verificar se o usuário está ativo.
        """
        return user.is_active
    
    def is_superuser(self, user: User) -> bool:
        """
        Verificar se o usuário é um superusuário.
        """
        return user.is_superuser
    

    
    def get_first_superuser(self, db: Session) -> Optional[User]:
        """
        Buscar o primeiro super usuário encontrado no sistema.
        Usado para verificar se já existe pelo menos um super user.
        """
        return db.query(User).filter(User.is_superuser == True).first()


# Instância global para uso nos endpoints
user = CRUDUser() 