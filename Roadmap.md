# Sem título

# Guia de Desenvolvimento: Prova de Conceito (PoC) - Intelectus

Este documento serve como um guia passo a passo para o desenvolvimento do backend do projeto Intelectus usando FastAPI. Cada etapa foi desenhada para ser clara e sequencial, facilitando o desenvolvimento e a colaboração.

## Fase 1: Configuração do Ambiente e Estrutura do Projeto

O objetivo desta fase é preparar todo o ambiente de desenvolvimento e criar uma estrutura de pastas lógica e escalável para a nossa aplicação.

### 1.1. Estrutura de Pastas

Vamos começar criando uma estrutura de pastas que separe as responsabilidades da aplicação, seguindo as melhores práticas para projetos FastAPI.

Bash

# 

`intelectus-backend/
├── app/
│   ├── __init__.py
│   ├── main.py             # Ponto de entrada da aplicação FastAPI
│   ├── core/               # Configurações, dependências globais
│   │   ├── __init__.py
│   │   └── config.py         # Variáveis de ambiente e configurações
│   ├── db/                 # Conexão com o banco de dados e sessão
│   │   ├── __init__.py
│   │   └── session.py        # Lógica para criar a sessão com o DB
│   ├── models/             # Modelos da tabela do SQLAlchemy
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── company.py
│   │   └── process.py
│   ├── schemas/            # Esquemas de validação de dados (Pydantic)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── company.py
│   │   └── process.py
│   ├── crud/               # Funções de manipulação de dados (Create, Read, Update, Delete)
│   │   ├── __init__.py
│   │   ├── crud_user.py
│   │   ├── crud_company.py
│   │   └── crud_process.py
│   ├── api/                # Endpoints da API (Rotas)
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py          # Roteador principal da API
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   ├── users.py
│   │       │   ├── companies.py
│   │       │   └── processes.py
│   ├── services/           # Lógica de negócio (ex: Web Scraping)
│   │   ├── __init__.py
│   │   └── rpi_scraper.py
│   └── security/           # Lógica de autenticação e segurança
│       ├── __init__.py
│       └── auth.py
├── .env                  # Arquivo para variáveis de ambiente (NUNCA versionar)
├── .gitignore            # Arquivo para ignorar arquivos no Git
└── requirements.txt      # Lista de dependências do projeto`

### 1.2. Ambiente Virtual e Dependências

É crucial usar um ambiente virtual para isolar as dependências do projeto.

1. **Criar e Ativar Ambiente Virtual:**Bash
    
    # 
    
    `python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate`
    
2. Instalar Dependências Essenciais:Bash
    
    O backend será construído com FastAPI em Python1111. Precisaremos de um servidor ASGI como o Uvicorn, SQLAlchemy para o ORM e Pydantic (que já vem com FastAPI) para validação.
    
    # 
    
    `pip install "fastapi[all]" sqlalchemy "psycopg2-binary" "python-dotenv" "passlib[bcrypt]" "python-jose[cryptography]"`
    
    - `fastapi[all]`: Instala o FastAPI e o servidor `uvicorn`.
    - `sqlalchemy`: O ORM para interagir com o banco de dados.
    - `psycopg2-binary`: Driver para conectar Python com PostgreSQL (Neon).
    - `python-dotenv`: Para carregar variáveis de ambiente do arquivo `.env`.
    - `passlib[bcrypt]`: Para hashing de senhas.
    - `python-jose[cryptography]`: Para criação e validação de tokens JWT (autenticação).
3. **Criar `requirements.txt`:**Bash
    
    # 
    
    `pip freeze > requirements.txt`
    

## Fase 2: Modelagem do Banco de Dados e Esquemas

Nesta fase, vamos traduzir o modelo de dados que definimos para código Python.

### 2.1. Configurar Conexão com o Banco de Dados

1. Arquivo .env:Snippet de código
    
    Crie o arquivo .env na raiz do projeto para armazenar a URL de conexão do seu banco Neon.
    
    # 
    
    `DATABASE_URL="postgresql://user:password@host:port/dbname"
    SECRET_KEY="sua_chave_secreta_para_jwt_muito_segura"
    ALGORITHM="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES=30`
    
2. app/core/config.py:
    
    Crie um arquivo para carregar essas variáveis para a aplicação.
    
3. app/db/session.py:
    
    Implemente a lógica para criar o motor (engine) do SQLAlchemy e a sessão de conexão com o banco de dados.
    

### 2.2. Criar Modelos SQLAlchemy (`app/models/`)

Crie um arquivo Python para cada entidade (`user.py`, `company.py`, `process.py`) e defina as classes que representarão as tabelas no banco de dados, usando a sintaxe do SQLAlchemy.

**Exemplo (`process.py`):**

Python

# 

`from sqlalchemy import Column, String, Date, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base # Uma classe base declarativa que você vai criar

class Process(Base):
    id = Column(...)
    company_id = Column(..., ForeignKey("company.id"))
    process_type = Column(Enum('brand', 'patent', ...), nullable=False)
    # ... outros campos ...
    company = relationship("Company")`

### 2.3. Criar Esquemas Pydantic (`app/schemas/`)

Os esquemas Pydantic definem a "forma" dos dados que a API espera receber e envia como resposta. Eles são cruciais para a validação automática de dados do FastAPI. 2

**Exemplo (`process.py`):**

Python

# 

`from pydantic import BaseModel
from datetime import date

# Esquema base com campos compartilhados
class ProcessBase(BaseModel):
    process_number: str
    title: str | None = None
    # ... outros campos ...

# Esquema para criação de um novo processo
class ProcessCreate(ProcessBase):
    pass

# Esquema para leitura de um processo (incluindo campos do DB como id)
class ProcessInDB(ProcessBase):
    id: int
    company_id: int

    class Config:
        orm_mode = True # Permite que o Pydantic leia dados de modelos ORM`

## Fase 3: Lógica de Negócio e Endpoints da API

Com os modelos prontos, vamos criar as funções para interagir com eles e expor essa lógica através de endpoints.

### 3.1. Funções CRUD (`app/crud/`)

Crie um arquivo para cada modelo (ex: `crud_process.py`) contendo as funções para:

- `get_process(db, process_id)`: Buscar um processo pelo ID.
- `get_processes(db)`: Buscar uma lista de processos.
- `create_process(db, process_schema)`: Criar um novo processo.
- `update_process(...)`: Atualizar um processo.
- `delete_process(...)`: Deletar um processo.

### 3.2. Autenticação e Segurança (`app/security/auth.py`)

Esta é uma parte crítica dos requisitos funcionais e não-funcionais. 3333

1. Implemente funções para:
    - `create_access_token()`: Gerar um token JWT para o usuário logado.
    - `verify_password()`: Comparar a senha enviada no login com a senha "hasheada" no banco.
    - `get_password_hash()`: Gerar o hash de uma senha para armazenar no banco.
2. Crie uma dependência (`get_current_user`) que possa ser usada nos endpoints para proteger rotas e obter o usuário logado a partir do token.

### 3.3. Endpoints da API (`app/api/v1/endpoints/`)

Crie os endpoints usando os `APIRouter` do FastAPI. Cada endpoint usará as funções CRUD para realizar as operações e os esquemas Pydantic para validação.

**Exemplo (`processes.py`):**

Python

# 

`from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, schemas, security

router = APIRouter()

@router.post("/", response_model=schemas.ProcessInDB)
def create_process(
    *,
    db: Session = Depends(...), # Dependência para obter a sessão do DB
    process_in: schemas.ProcessCreate,
    current_user: models.User = Depends(security.get_current_user) # Protege a rota
):
    # Lógica para associar o processo à empresa do usuário logado
    process = crud.process.create(db=db, obj_in=process_in)
    return process`

### 3.4. Montagem da Aplicação (`app/main.py`)

No arquivo `main.py`, importe os roteadores da API e monte a aplicação FastAPI principal.

Python

# 

`from fastapi import FastAPI
from app.api.v1 import api_router

app = FastAPI(title="Intelectus API")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Intelectus API"}`

## Fase 4: Funcionalidades Avançadas (Requisitos Essenciais)

Com a base da API pronta, focamos nas funcionalidades que tornam o Intelectus único.

### 4.1. Serviço de Web Scraping (`app/services/rpi_scraper.py`)

Esta etapa implementa um dos principais requisitos funcionais. 4

1. 
    
    **Escolher a Biblioteca:** Analise o site do INPI para decidir entre `BeautifulSoup` (para HTML) ou `xml.etree.ElementTree` (para XML), conforme mencionado na documentação do projeto. 555
    
2. **Implementar o Scraper:** Crie uma função ou classe que:
    - Acessa a URL da RPI.
    - Faz o download do arquivo da revista. 6
    - Extrai os dados relevantes dos processos (número, titular, decisão, etc.). 7
    - Retorna os dados em um formato estruturado (lista de dicionários ou objetos Pydantic).
3. **Criar um Endpoint de Sincronização:** Crie um endpoint (ex: `POST /api/v1/sync/rpi`) que acione o serviço de scraping. Este endpoint deve ser protegido e acessível apenas por administradores. 8888

### 4.2. Sistema de Matching e Alertas

Esta é a "inteligência" do sistema. 9999

1. **Lógica de Comparação:** Após o scraping, crie uma função que:
    - Percorra os dados extraídos da RPI.
    - Para cada dado, compare com os processos cadastrados pelos usuários no banco de dados. 10
    - Use lógicas de comparação flexíveis para lidar com variações de nome, etc. 11
2. **Criação de Alertas:**
    - Quando um "match" for encontrado, crie um registro na tabela `Alert`, associando-o ao usuário e ao processo correspondente.
    - Implemente um endpoint para que o usuário possa consultar seus alertas não lidos. 12121212

---

Seguindo este guia, você construirá a PoC do Intelectus de forma estruturada, cobrindo todos os requisitos técnicos e funcionais definidos na documentação do seu projeto. Boa programação!