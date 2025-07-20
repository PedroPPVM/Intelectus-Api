from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base_class import Base


# Criar engine do SQLAlchemy
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries em desenvolvimento
    pool_pre_ping=True,   # Verificar conexões antes de usar
)

# Criar sessionmaker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Dependência para obter sessão do banco
def get_db():
    """
    Dependência do FastAPI para injeção da sessão do banco de dados.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """
    Context manager para obter sessão de banco.
    Usado em scripts CLI e operações manuais.
    """
    return SessionLocal()


# As tabelas são criadas via Alembic migrations.
# Use: python cli.py db upgrade 