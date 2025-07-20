from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate


class CRUDCompany:
    """
    Operações CRUD para o modelo Company.
    """
    
    def create(self, db: Session, *, obj_in: CompanyCreate) -> Company:
        """
        Criar uma nova empresa.
        """
        # Criar empresa
        db_company = Company(
            name=obj_in.name,
            document=obj_in.document,
            email=obj_in.email,
            phone=obj_in.phone,
            address=obj_in.address,
            city=obj_in.city,
            state=obj_in.state,
            zip_code=obj_in.zip_code,
            country=obj_in.country
        )
        
        db.add(db_company)
        db.flush()  # Para obter o ID
        
        # Associar com usuários se fornecidos
        if obj_in.user_ids:
            users = db.query(User).filter(User.id.in_(obj_in.user_ids)).all()
            db_company.users.extend(users)
        
        db.commit()
        db.refresh(db_company)
        return db_company
    
    def get(self, db: Session, id: UUID) -> Optional[Company]:
        """
        Buscar empresa por ID.
        """
        return db.query(Company).filter(Company.id == id).first()
    
    def get_by_document(self, db: Session, document: str) -> Optional[Company]:
        """
        Buscar empresa por documento (CNPJ/CPF).
        """
        return db.query(Company).filter(Company.document == document).first()
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Company]:
        """
        Buscar múltiplas empresas com paginação.
        """
        return db.query(Company).offset(skip).limit(limit).all()
    
    def get_by_user(self, db: Session, user_id: UUID) -> List[Company]:
        """
        Buscar empresas associadas a um usuário.
        """
        user = db.query(User).filter(User.id == user_id).first()
        return user.companies if user else []
    
    def search_by_name(
        self, db: Session, name: str, skip: int = 0, limit: int = 100
    ) -> List[Company]:
        """
        Buscar empresas por nome (busca parcial).
        """
        return (
            db.query(Company)
            .filter(Company.name.ilike(f"%{name}%"))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update(
        self, db: Session, *, db_obj: Company, obj_in: CompanyUpdate
    ) -> Company:
        """
        Atualizar uma empresa existente.
        """
        update_data = obj_in.dict(exclude_unset=True)
        
        # Atualizar relacionamentos com usuários
        if "user_ids" in update_data:
            user_ids = update_data.pop("user_ids")
            if user_ids is not None:
                users = db.query(User).filter(User.id.in_(user_ids)).all()
                db_obj.users = users
        
        # Atualizar demais campos
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: UUID) -> Optional[Company]:
        """
        Deletar uma empresa.
        """
        obj = db.query(Company).filter(Company.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    



# Instância global para uso nos endpoints
company = CRUDCompany() 