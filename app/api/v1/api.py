from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, companies, processes, alerts, memberships, company_processes


api_router = APIRouter()

# Incluir roteadores dos endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(processes.router, prefix="/processes", tags=["processes"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(memberships.router, prefix="/memberships", tags=["memberships"])

# Endpoints orientados a company - Roadmap Fase 3.1.2
api_router.include_router(
    company_processes.router, 
    prefix="/companies", 
    tags=["company-processes"]
) 