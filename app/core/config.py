from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List


class Settings(BaseSettings):
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=120, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Application
    project_name: str = Field(default="Intelectus API", env="PROJECT_NAME")
    version: str = Field(default="0.1.0", env="VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # CORS - Segurança em produção
    cors_origins: Optional[str] = Field(
        default=None, 
        env="CORS_ORIGINS",
        description="Lista de origens permitidas separadas por vírgula. Em produção, não deixar vazio."
    )
    
    # INPI Scraping
    rpi_base_url: str = Field(default="https://revistas.inpi.gov.br", env="RPI_BASE_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Instância global das configurações
settings = Settings() 