from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.api.v1.api import api_router


# Metadata para documentação OpenAPI/Swagger
tags_metadata = [
    {
        "name": "auth",
        "description": "**Autenticação e autorização.** Endpoints para login, registro e gestão de tokens JWT.",
    },
    {
        "name": "users", 
        "description": "**Gestão de usuários.** CRUD completo para usuários do sistema, incluindo associações com empresas.",
    },
    {
        "name": "companies",
        "description": "**Gestão de empresas.** CRUD para empresas/organizações e relacionamentos N:N com usuários.",
    },
    {
        "name": "processes",
        "description": "**Processos de PI.** Gestão completa de processos de propriedade intelectual (marcas, patentes, etc.).",
    },
    {
        "name": "alerts",
        "description": "**Sistema de alertas.** Notificações sobre mudanças de status em processos de PI.",
    },
]


def create_application() -> FastAPI:
    """
    Factory function para criar a aplicação FastAPI.
    """
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        debug=settings.debug,
        description="""
        🔍 API para Monitoramento de Processos de Propriedade Intelectual
        
        A Intelectus API oferece uma solução completa para monitoramento automatizado de processos 
        de propriedade intelectual junto ao INPI (Instituto Nacional da Propriedade Industrial).
        
        🎯 Funcionalidades Principais:
        
        - 👥 Gestão de Usuários e Empresas com relacionamento N:N
        - 📋 Cadastro e Monitoramento de processos de PI (marcas, patentes, desenhos, etc.)
        - 🔔 Sistema de Alertas automáticos sobre mudanças de status
        - 🔒 Autenticação JWT com controle de permissões
        - 📊 Filtros e Buscas avançadas em todos os recursos
        - 🤖 Integração preparada para web scraping do INPI
        
        🚀 Como Usar:
        
        1. Registre-se via `/api/v1/auth/register`
        2. Faça login via `/api/v1/auth/login` para obter seu token JWT
        3. Use o token no header: `Authorization: Bearer <seu-token>`
        4. Explore os endpoints para gerenciar seus dados
        
        🔐 Autenticação:
        
        Todos os endpoints (exceto registro e login) requerem autenticação via JWT.
        Use o botão "Authorize" nesta página para inserir seu token.
        
        🏢 Relacionamentos:
        
        - Users ↔ Companies: Relacionamento N:N (um usuário pode gerenciar várias empresas)
        - Companies → Processes: Uma empresa pode ter vários processos
        - Users → Alerts: Usuários recebem alertas sobre seus processos
        """,
        docs_url="/docs",
        redoc_url="/redoc", 
        openapi_url="/openapi.json",
        openapi_tags=tags_metadata
    )
    
    # Configurar CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, especificar domínios específicos
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Middleware de segurança (hosts confiáveis)
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*.intelectus.com.br"]
        )
    
    # Handler global para erros de banco de dados
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor"}
        )
    
    # Incluir roteadores da API
    app.include_router(api_router, prefix="/api/v1")
    
    # Rotas básicas
    @app.get(
        "/",
        tags=["root"],
        summary="Informações da API",
        description="Endpoint raiz com informações gerais sobre a API"
    )
    def read_root():
        return {
            "project": settings.project_name,
            "version": settings.version,
            "status": "running",
            "message": "🚀 Intelectus API está funcionando!",
            "documentation": {
                "swagger_ui": "/docs",
                "redoc": "/redoc",
                "openapi_json": "/openapi.json"
            },
            "api": "/api/v1"
        }
    
    @app.get(
        "/health",
        tags=["monitoring"],
        summary="Health Check",
        description="Endpoint para monitoramento de saúde da aplicação"
    )
    def health_check():
        """
        **Health check** para monitoramento da aplicação.
        
        Retorna o status da API e conectividade com o banco de dados.
        Útil para sistemas de monitoramento e load balancers.
        """
        return {
            "status": "healthy",
            "database": "connected", 
            "version": settings.version,
            "environment": "development" if settings.debug else "production"
        }
    
    @app.get(
        "/api/v1",
        tags=["api-info"],
        summary="Informações da API v1",
        description="Metadados e endpoints disponíveis na versão 1 da API"
    )
    def api_info():
        """
        **Informações sobre a API v1.**
        
        Lista todos os grupos de endpoints disponíveis e suas funcionalidades.
        """
        return {
            "message": "🔍 Intelectus API v1 - Monitoramento de PI",
            "version": settings.version,
            "endpoints": {
                "auth": {
                    "path": "/api/v1/auth",
                    "description": "Autenticação (login, registro, tokens JWT)"
                },
                "users": {
                    "path": "/api/v1/users", 
                    "description": "Gestão de usuários e relacionamentos N:N"
                },
                "companies": {
                    "path": "/api/v1/companies",
                    "description": "CRUD de empresas e associações"
                },
                "processes": {
                    "path": "/api/v1/processes",
                    "description": "Processos de PI (marcas, patentes, etc.)"
                },
                "alerts": {
                    "path": "/api/v1/alerts",
                    "description": "Sistema de notificações e alertas"
                }
            },
            "features": [
                "🔒 Autenticação JWT",
                "👥 Relacionamento N:N Users ↔ Companies", 
                "📋 Gestão completa de processos de PI",
                "🔔 Sistema de alertas automático",
                "📊 Filtros e paginação avançados",
                "🛡️ Controle de permissões granular"
            ],
            "documentation": "/docs"
        }
    
    return app


app = create_application() 