from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.process import Process
from app.models.company import Company
from app.models.user import User
from app.schemas.process import ProcessCreate, ProcessUpdate


class CRUDProcess:
    """
    Operações CRUD para o modelo Process.
    """
    
    def create(self, db: Session, *, obj_in: ProcessCreate) -> Process:
        """
        Criar um novo processo.
        """
        # Criar processo
        db_process = Process(
            process_number=obj_in.process_number,
            title=obj_in.title,
            short_title=obj_in.short_title,
            description=obj_in.description,
            process_type=obj_in.process_type,
            status=obj_in.status,
            filing_date=obj_in.filing_date,
            publication_date=obj_in.publication_date,
            grant_date=obj_in.grant_date,
            expiry_date=obj_in.expiry_date,
            applicant_name=obj_in.applicant_name,
            applicant_document=obj_in.applicant_document,
            nice_classification=obj_in.nice_classification,
            ipc_classification=obj_in.ipc_classification,
            company_id=obj_in.company_id
        )
        
        db.add(db_process)
        db.commit()
        db.refresh(db_process)
        return db_process
    
    def get(self, db: Session, id: UUID) -> Optional[Process]:
        """
        Buscar processo por ID.
        """
        return db.query(Process).filter(Process.id == id).first()
    
    def get_by_number(self, db: Session, process_number: str) -> Optional[Process]:
        """
        Buscar processo por número.
        """
        return db.query(Process).filter(Process.process_number == process_number).first()
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Process]:
        """
        Buscar múltiplos processos com paginação.
        """
        return db.query(Process).offset(skip).limit(limit).all()
    
    def get_by_company(
        self, db: Session, company_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Process]:
        """
        Buscar processos de uma empresa específica.
        """
        return (
            db.query(Process)
            .filter(Process.company_id == company_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_user_companies(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Process]:
        """
        Buscar processos de todas as empresas associadas a um usuário.
        """
        return (
            db.query(Process)
            .join(Company)
            .join(Company.users)
            .filter(User.id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def search_by_title(
        self, db: Session, title: str, skip: int = 0, limit: int = 100
    ) -> List[Process]:
        """
        Buscar processos por título (busca parcial).
        """
        return (
            db.query(Process)
            .filter(Process.title.ilike(f"%{title}%"))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def filter_by_type(
        self, db: Session, process_type: str, skip: int = 0, limit: int = 100
    ) -> List[Process]:
        """
        Filtrar processos por tipo.
        """
        return (
            db.query(Process)
            .filter(Process.process_type == process_type)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def filter_by_status(
        self, db: Session, status: str, skip: int = 0, limit: int = 100
    ) -> List[Process]:
        """
        Filtrar processos por status.
        """
        return (
            db.query(Process)
            .filter(Process.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update(
        self, db: Session, *, db_obj: Process, obj_in: ProcessUpdate
    ) -> Process:
        """
        Atualizar um processo existente.
        """
        update_data = obj_in.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: UUID) -> Optional[Process]:
        """
        Deletar um processo.
        """
        obj = db.query(Process).filter(Process.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def update_scraped_at(self, db: Session, *, id: UUID) -> Optional[Process]:
        """
        Atualizar timestamp de último scraping.
        """
        from datetime import datetime
        
        obj = db.query(Process).filter(Process.id == id).first()
        if obj:
            obj.last_scraped_at = datetime.utcnow()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj
    
    # ===== FUNÇÕES ORIENTADAS A COMPANY (Roadmap Fase 3.1.2) =====
    
    def get_by_company_optimized(
        self, 
        db: Session, 
        company_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[Process]:
        """
        Buscar processos de uma empresa específica - VERSÃO OTIMIZADA.
        
        Usa índices compostos para performance máxima:
        - ix_process_company_created: ordenação por data
        - ix_process_company_updated: ordenação por atualização
        
        Args:
            company_id: ID da empresa
            skip: Paginação - registros para pular
            limit: Paginação - máximo de registros
            order_by: Campo para ordenação ('created_at', 'updated_at', 'title')
            order_desc: Se True ordena descendente, False ascendente
        """
        query = db.query(Process).filter(Process.company_id == company_id)
        
        # Aplicar ordenação usando índices otimizados
        if order_by == "created_at":
            query = query.order_by(Process.created_at.desc() if order_desc else Process.created_at.asc())
        elif order_by == "updated_at":
            query = query.order_by(Process.updated_at.desc() if order_desc else Process.updated_at.asc())
        elif order_by == "title":
            query = query.order_by(Process.title.desc() if order_desc else Process.title.asc())
        else:
            # Default para created_at
            query = query.order_by(Process.created_at.desc() if order_desc else Process.created_at.asc())
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_company_and_type(
        self, 
        db: Session, 
        company_id: UUID, 
        process_type: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Process]:
        """
        Buscar processos por empresa e tipo - USA ÍNDICE OTIMIZADO.
        
        Usa o índice ix_process_company_type para performance máxima.
        """
        return (
            db.query(Process)
            .filter(
                Process.company_id == company_id,
                Process.process_type == process_type
            )
            .order_by(Process.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_company_and_status(
        self, 
        db: Session, 
        company_id: UUID, 
        status: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Process]:
        """
        Buscar processos por empresa e status - USA ÍNDICE OTIMIZADO.
        
        Usa o índice ix_process_company_status para performance máxima.
        """
        return (
            db.query(Process)
            .filter(
                Process.company_id == company_id,
                Process.status == status
            )
            .order_by(Process.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_company_and_number(
        self, db: Session, company_id: UUID, process_number: str
    ) -> Optional[Process]:
        """
        Buscar processo por empresa e número - USA ÍNDICE ÚNICO OTIMIZADO.
        
        Usa o índice único ix_process_company_number para performance máxima.
        Ideal para validações e buscas específicas.
        """
        return (
            db.query(Process)
            .filter(
                Process.company_id == company_id,
                Process.process_number == process_number
            )
            .first()
        )
    
    def search_by_company_and_title(
        self, 
        db: Session, 
        company_id: UUID, 
        title: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Process]:
        """
        Buscar processos por empresa e título - USA ÍNDICE OTIMIZADO.
        
        Usa o índice ix_process_company_title_search para performance em buscas.
        """
        return (
            db.query(Process)
            .filter(
                Process.company_id == company_id,
                Process.title.ilike(f"%{title}%")
            )
            .order_by(Process.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_by_company(self, db: Session, company_id: UUID) -> int:
        """
        Contar total de processos de uma empresa.
        
        Performance otimizada com índice company_id.
        """
        return db.query(Process).filter(Process.company_id == company_id).count()
    
    def count_by_company_and_type(self, db: Session, company_id: UUID, process_type: str) -> int:
        """
        Contar processos de uma empresa por tipo.
        
        Usa índice ix_process_company_type.
        """
        return (
            db.query(Process)
            .filter(
                Process.company_id == company_id,
                Process.process_type == process_type
            )
            .count()
        )
    
    def count_by_company_and_status(self, db: Session, company_id: UUID, status: str) -> int:
        """
        Contar processos de uma empresa por status.
        
        Usa índice ix_process_company_status.
        """
        return (
            db.query(Process)
            .filter(
                Process.company_id == company_id,
                Process.status == status
            )
            .count()
        )
    
    def get_company_process_stats(self, db: Session, company_id: UUID) -> dict:
        """
        Estatísticas completas dos processos de uma empresa.
        
        Retorna contadores por tipo, status e totais usando índices otimizados.
        Ideal para dashboards e relatórios.
        """
        from app.models.process import ProcessType, ProcessStatus
        
        # Totais gerais
        total_processes = self.count_by_company(db, company_id)
        
        # Por tipo
        type_stats = {}
        for process_type in ProcessType:
            count = self.count_by_company_and_type(db, company_id, process_type.value)
            type_stats[process_type.value] = count
        
        # Por status
        status_stats = {}
        for status in ProcessStatus:
            count = self.count_by_company_and_status(db, company_id, status.value)
            status_stats[status.value] = count
        
        # Processos recentes (últimos 30 dias)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = (
            db.query(Process)
            .filter(
                Process.company_id == company_id,
                Process.created_at >= thirty_days_ago
            )
            .count()
        )
        
        return {
            "company_id": str(company_id),
            "total_processes": total_processes,
            "by_type": type_stats,
            "by_status": status_stats,
            "recent_processes_30_days": recent_count,
            "generated_at": datetime.utcnow().isoformat()
        }


# Instância global para uso nos endpoints
process = CRUDProcess() 