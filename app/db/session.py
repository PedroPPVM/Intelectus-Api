import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy import event
from app.core.config import settings
from app.db.base_class import Base

# Configurar logging do SQLAlchemy
# Reduzir verbosidade das queries SQL
sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
sqlalchemy_logger.setLevel(logging.WARNING)  # Apenas WARNING e ERROR

# Criar engine do SQLAlchemy
engine = create_engine(
    settings.database_url,
    echo=False,  # Desabilitar echo padrão (vamos usar logging customizado)
    pool_pre_ping=True,   # Verificar conexões antes de usar
)

# Configurar logging customizado para queries SQL (opcional, apenas se DEBUG=True)
if settings.debug:
    # Criar logger customizado para queries SQL com formatação destacada
    sql_logger = logging.getLogger('intelectus.sql')
    sql_logger.setLevel(logging.INFO)
    
    # Handler para destacar queries SQL
    if not sql_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '\033[90m[SQL]\033[0m %(message)s'  # Cinza para queries SQL
        )
        handler.setFormatter(formatter)
        sql_logger.addHandler(handler)
        sql_logger.propagate = False
    
    # Event listener para capturar queries SQL e logar de forma destacada
    @event.listens_for(Engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        # Logar apenas se for uma query SELECT (para reduzir poluição)
        if statement.strip().upper().startswith('SELECT'):
            sql_logger.info(f"{statement[:100]}..." if len(statement) > 100 else statement)

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