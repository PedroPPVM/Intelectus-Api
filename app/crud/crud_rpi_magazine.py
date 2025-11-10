from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from uuid import UUID

from app.models.rpi_magazine import RPIMagazine
from app.models.process import ProcessType
from app.schemas.rpi_magazine import RPIMagazineCreate, RPIMagazineUpdate


class CRUDRPIMagazine:
    """
    Operações CRUD para o modelo RPIMagazine.
    
    Uso interno apenas - não exposto via API.
    """
    
    def create(self, db: Session, *, obj_in: RPIMagazineCreate) -> RPIMagazine:
        """
        Criar uma nova revista RPI.
        """
        db_magazine = RPIMagazine(
            process_type=obj_in.process_type,
            magazine_identifier=obj_in.magazine_identifier,
            url=obj_in.url,
            publication_date=obj_in.publication_date,
            last_checked_at=obj_in.last_checked_at,
            processed_at=obj_in.processed_at
        )
        
        db.add(db_magazine)
        db.commit()
        db.refresh(db_magazine)
        return db_magazine
    
    def get(self, db: Session, id: UUID) -> Optional[RPIMagazine]:
        """
        Buscar revista por ID.
        """
        return db.query(RPIMagazine).filter(RPIMagazine.id == id).first()
    
    def get_by_type_and_identifier(
        self, 
        db: Session, 
        process_type: ProcessType, 
        magazine_identifier: str
    ) -> Optional[RPIMagazine]:
        """
        Buscar revista por tipo e identificador.
        
        Usado para verificar se já temos uma revista específica.
        """
        return (
            db.query(RPIMagazine)
            .filter(
                RPIMagazine.process_type == process_type,
                RPIMagazine.magazine_identifier == magazine_identifier
            )
            .first()
        )
    
    def get_latest_by_type(
        self, 
        db: Session, 
        process_type: ProcessType
    ) -> Optional[RPIMagazine]:
        """
        Buscar a última revista por tipo (mais recente por created_at).
        
        Usado para comparar com a última revista disponível no site.
        """
        return (
            db.query(RPIMagazine)
            .filter(RPIMagazine.process_type == process_type)
            .order_by(desc(RPIMagazine.created_at))
            .first()
        )
    
    def update(
        self, 
        db: Session, 
        *, 
        db_obj: RPIMagazine, 
        obj_in: RPIMagazineUpdate
    ) -> RPIMagazine:
        """
        Atualizar uma revista existente.
        """
        update_data = obj_in.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_or_create(
        self,
        db: Session,
        *,
        process_type: ProcessType,
        magazine_identifier: str,
        url: str,
        publication_date: Optional = None,
        last_checked_at: Optional = None
    ) -> tuple[RPIMagazine, bool]:
        """
        Buscar ou criar uma revista.
        
        Returns:
            tuple: (revista, criada) - onde criada é True se foi criada agora
        """
        # Tentar buscar existente
        magazine = self.get_by_type_and_identifier(
            db, process_type, magazine_identifier
        )
        
        if magazine:
            # Atualizar last_checked_at se fornecido
            if last_checked_at:
                update_data = RPIMagazineUpdate(last_checked_at=last_checked_at)
                magazine = self.update(db, db_obj=magazine, obj_in=update_data)
            return magazine, False
        
        # Criar nova revista
        create_data = RPIMagazineCreate(
            process_type=process_type,
            magazine_identifier=magazine_identifier,
            url=url,
            publication_date=publication_date,
            last_checked_at=last_checked_at
        )
        magazine = self.create(db, obj_in=create_data)
        return magazine, True


# Instância global para uso nos services
rpi_magazine = CRUDRPIMagazine()

