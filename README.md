# 🎯 Intelectus API

**API REST robusta para gerenciar propriedade intelectual com sistema avançado de membership e auditoria.**

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Latest-blue.svg)
![JWT](https://img.shields.io/badge/Auth-JWT-orange.svg)
![Alembic](https://img.shields.io/badge/Migrations-Alembic-red.svg)

---

## ⚡ **Informações Cruciais**

### **⚠️ Código Legado - NÃO MODIFICAR**
- `app/services/scraping_service.py` - **Código legado crítico**
- `app/services/pdf_reader.py` - **Código legado crítico**
- O responsável original não trabalha mais no projeto
- Modificações podem quebrar funcionalidades críticas

### **🔐 Variáveis de Ambiente Obrigatórias**
**Desenvolvimento:**
- `DATABASE_URL` - URL do banco PostgreSQL
- `SECRET_KEY` - Chave secreta para JWT
- `DEBUG=True` - Modo debug

**Produção:**
- `DATABASE_URL` - URL do banco de produção
- `SECRET_KEY` - Chave secreta forte (256 bits)
- `CORS_ORIGINS` - **OBRIGATÓRIO** - Domínios permitidos separados por vírgula
- `DEBUG=False` - **CRÍTICO** - Desativar debug em produção

### **🛡️ Segurança Implementada**
- ✅ Rate limiting: Login (5/min), Registro (3/min) por IP
- ✅ CORS configurável via `CORS_ORIGINS`
- ✅ JWT com expiração configurável
- ✅ Hash de senhas com bcrypt

---

## 🚀 **Início Rápido**

### **Pré-requisitos**
- Python 3.12+
- PostgreSQL (ou Docker)
- Git

### **1. Clonar e Configurar**
```bash
# Clonar repositório
git clone <url-do-repo>
cd Intelectus-Api

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependências (inclui slowapi para rate limiting)
pip install -r requirements.txt
```

### **2. Configurar Variáveis de Ambiente**
```bash
# Criar arquivo .env
cat > .env << EOF
# Banco de Dados
DATABASE_URL=postgresql://admin:Inicio@123@localhost:5432/intelectus_db

# Segurança
SECRET_KEY=sua-chave-secreta-aqui-gerar-256-bits
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Aplicação
PROJECT_NAME=Intelectus API
VERSION=0.1.0
DEBUG=True

# CORS (em produção, definir domínios específicos)
# CORS_ORIGINS=https://app.intelectus.com.br,https://admin.intelectus.com.br

# INPI Scraping
RPI_BASE_URL=https://revistas.inpi.gov.br
EOF

# Ou configurar PostgreSQL com Docker
docker-compose up -d
```

### **3. Usar o CLI para Setup**
```bash
# Testar conexão
python cli.py dev test-connection

# Aplicar migrations
python cli.py db upgrade

# Criar administrador
python cli.py dev create-admin

# Iniciar servidor
python cli.py server run
```

### **4. Acessar API**
- **Swagger/OpenAPI**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

**⚠️ Nota:** Rate limiting está ativo:
- Login: máximo 5 tentativas por minuto por IP
- Registro: máximo 3 tentativas por minuto por IP

---

## 🏗️ **Arquitetura**

### **📁 Estrutura do Projeto**
```
Intelectus-Api/
├── app/                        # Código principal da API
│   ├── api/v1/endpoints/       # 🌐 Endpoints REST
│   │   ├── auth.py            # Autenticação (login, register)
│   │   ├── users.py           # Gestão de usuários
│   │   ├── companies.py       # Gestão de empresas
│   │   ├── processes.py       # Processos PI
│   │   ├── alerts.py          # Sistema de alertas
│   │   └── memberships.py     # Sistema avançado de membership
│   ├── models/                # 🗄️ Modelos SQLAlchemy
│   │   ├── user.py            # Usuários
│   │   ├── company.py         # Empresas
│   │   ├── process.py         # Processos
│   │   ├── alert.py           # Alertas
│   │   └── membership.py      # Sistema de membership
│   ├── schemas/               # 📋 Validação Pydantic
│   ├── crud/                  # 📊 Operações de banco
│   ├── services/              # 🎯 Lógica de negócio
│   │   └── membership_service.py  # Service robusto
│   ├── security/              # 🔐 Autenticação e segurança
│   ├── db/                    # 🗄️ Configuração do banco
│   └── core/                  # ⚙️ Configurações
├── alembic/                   # 🔄 Migrations
├── cli.py                     # 🎯 CLI administrativo
├── docker-compose.yml         # 🐳 PostgreSQL
└── requirements.txt           # 📦 Dependências
```

### **🗄️ Modelos de Dados**

#### **Principais Entidades**
- **👤 User** - Usuários do sistema
- **🏢 Company** - Empresas/organizações  
- **📋 Process** - Processos de propriedade intelectual
- **🔔 Alert** - Alertas e notificações

#### **Sistema de Membership Avançado**
- **👥 UserCompanyMembership** - Relacionamentos com roles
- **📊 MembershipHistory** - Auditoria completa
- **🔐 UserCompanyPermission** - Permissões granulares

---

## 🎯 **CLI Administrativo**

O projeto inclui um **CLI poderoso** para todas as operações administrativas:

### **📋 Comandos Principais**
```bash
# 🗄️ Banco de Dados
python cli.py db status          # Status das migrations
python cli.py db upgrade         # Aplicar migrations  
python cli.py db create "msg"    # Criar nova migration
python cli.py db history         # Ver histórico

# 🛠️ Desenvolvimento
python cli.py dev create-admin   # Criar administrador
python cli.py dev test-connection # Testar banco

# 🚀 Servidor
python cli.py server run         # Iniciar desenvolvimento
python cli.py server run --port 3000  # Porta customizada

# 👥 Membership
python cli.py membership stats --company-id UUID

# ℹ️ Sistema
python cli.py info               # Informações gerais
python cli.py --help            # Ajuda completa
```

**📚 Documentação completa**: [CLI-GUIDE.md](CLI-GUIDE.md)

---

## 🌐 **API REST**

### **🔐 Autenticação**
```bash
# Registrar usuário
POST /api/v1/auth/register
{
  "email": "usuario@exemplo.com",
  "full_name": "João Silva", 
  "password": "minhasenha123"
}

# Login
POST /api/v1/auth/login  
{
  "email": "usuario@exemplo.com",
  "password": "minhasenha123"
}

# Resposta
{
  "access_token": "eyJ0eXAiOiJKV1Q...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### **👥 Sistema de Membership**

#### **Criar Membership com Auditoria**
```bash
POST /api/v1/memberships/
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef",
  "role": "admin",
  "permissions": ["read_processes", "create_processes", "manage_users"],
  "reason": "Promovido a administrador do projeto"
}
```

#### **Roles Disponíveis**
- **👑 `owner`** - Proprietário (acesso total)
- **🛡️ `admin`** - Administrador (gestão completa)
- **👤 `member`** - Membro básico
- **👀 `viewer`** - Apenas visualização

#### **Permissões Granulares**
- `read_processes`, `create_processes`, `update_processes`, `delete_processes`
- `read_company_data`, `update_company_data`
- `manage_users`, `view_reports`, `manage_billing`

### **🏢 Gestão de Empresas**
```bash
# Listar empresas do usuário
GET /api/v1/companies/

# Criar empresa
POST /api/v1/companies/
{
  "name": "Minha Empresa Ltda",
  "document": "12345678000199",
  "email": "contato@minhaempresa.com"
}

# Ver membros da empresa
GET /api/v1/memberships/companies/{company_id}/members
```

### **📋 Processos de PI**
```bash
# Listar processos
GET /api/v1/processes/

# Criar processo
POST /api/v1/processes/
{
  "process_number": "BR402021123456-7",
  "title": "Sistema de Gestão Intelectual",
  "process_type": "software",
  "company_id": "987fcdeb-51a2-43d1-b123-456789abcdef"
}
```

### **🔔 Sistema de Alertas**
```bash
# Alertas do usuário
GET /api/v1/alerts/

# Marcar como lido
PATCH /api/v1/alerts/{alert_id}/read
```

---

## 🗄️ **Migrations e Banco**

### **Sistema Profissional com Alembic**
```bash
# Ver status
python cli.py db status

# Criar migration após mudança no modelo
python cli.py db create "Adicionar campo avatar no usuário"

# Aplicar migrations
python cli.py db upgrade

# Reverter (cuidado!)
python cli.py db downgrade -1

# Ver histórico
python cli.py db history
```

### **🔧 Variáveis de Ambiente**

#### **Desenvolvimento (.env)**
```bash
# Banco de Dados
DATABASE_URL=postgresql://admin:Inicio@123@localhost:5432/intelectus_db

# Segurança (OBRIGATÓRIO)
SECRET_KEY=sua-chave-secreta-256-bits-gerar-aleatoriamente
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Aplicação
PROJECT_NAME=Intelectus API
VERSION=0.1.0
DEBUG=True

# CORS (em desenvolvimento, não é necessário)
# Em produção, definir CORS_ORIGINS
```

#### **Produção (.env)**
```bash
# Banco de Dados
DATABASE_URL=postgresql://user:password@db-host:5432/intelectus_db

# Segurança (CRÍTICO)
SECRET_KEY=chave-super-secreta-256-bits-aleatoria
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Aplicação
PROJECT_NAME=Intelectus API
VERSION=0.1.0
DEBUG=False

# CORS (OBRIGATÓRIO EM PRODUÇÃO)
CORS_ORIGINS=https://app.intelectus.com.br,https://admin.intelectus.com.br

# INPI Scraping
RPI_BASE_URL=https://revistas.inpi.gov.br
```

**⚠️ IMPORTANTE:** Em produção, `CORS_ORIGINS` é obrigatório. Sem ele, todas as origens serão bloqueadas por segurança.

**📚 Guia completo**: [MIGRATIONS.md](MIGRATIONS.md)

---

## 🛡️ **Segurança**

### **🔐 Autenticação JWT**
- Tokens JWT com expiração configurável
- Hash de senhas com bcrypt  
- Refresh tokens (configurável)

### **🎭 Sistema de Permissões**
- **Superusuários** - acesso administrativo total
- **Roles por empresa** - owner, admin, member, viewer
- **Permissões granulares** - controle fino de acesso
- **Auditoria completa** - quem, quando, o que, por que

### **🛡️ Middleware de Segurança**
- **CORS configurado** - Configurável via `CORS_ORIGINS` (obrigatório em produção)
- **TrustedHost middleware** - Proteção contra host header attacks
- **Rate limiting** - Proteção contra brute force:
  - Login: 5 tentativas por minuto por IP
  - Registro: 3 tentativas por minuto por IP
- **Validação automática** de inputs via Pydantic

---

## 📊 **Recursos Avançados**

### **👥 Membership com Auditoria**
- **3 tabelas especializadas** para relacionamentos User↔Company
- **Histórico completo** de mudanças com IP e timestamp
- **Permissões granulares** por empresa
- **Soft/hard delete** com motivos
- **Estatísticas** e dashboards

### **🎯 CLI Rico e Intuitivo**
- **Interface colorida** com Rich
- **Tabelas organizadas** para informações
- **Progress bars** para operações longas
- **Confirmações interativas** para comandos perigosos
- **Help contextual** em todos os níveis

### **📈 Performance e Escalabilidade**
- **Índices otimizados** no banco
- **Queries eficientes** com SQLAlchemy
- **Paginação** em todos os endpoints
- **UUIDs** como chaves primárias
- **Conexão pool** configurada

---

## 🧪 **Testes e Desenvolvimento**

### **🔌 Testes Rápidos**
```bash
# Testar conexão com banco
python cli.py dev test-connection

# Testar API
python cli.py server test

# Ver status geral
python cli.py info
```

### **🚀 Ambiente de Desenvolvimento**
```bash
# Servidor com reload automático
python cli.py server run

# Servidor em porta específica  
python cli.py server run --port 3000

# Servidor produção (com uvicorn)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Ou com gunicorn (recomendado para produção)
# Instalar: pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### **🐳 Docker (Opcional)**
```bash
# Iniciar PostgreSQL com Docker Compose
docker-compose up -d

# Verificar status
docker-compose ps

# Parar PostgreSQL
docker-compose down
```

**Configuração do docker-compose.yml:**
- Usuário: `admin`
- Senha: `Inicio@123`
- Banco: `intelectus_db`
- Porta: `5432`

---

## 📚 **Documentação**

### **📋 Documentação Interativa**
- **Swagger UI**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc  
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### **📖 Guias Detalhados**
- [🎯 CLI-GUIDE.md](CLI-GUIDE.md) - Manual completo do CLI
- [🗄️ MIGRATIONS.md](MIGRATIONS.md) - Guia de migrations  
- [🗺️ Roadmap.md](Roadmap.md) - Histórico de desenvolvimento

### **🎨 Exemplos de Uso**
Todos os endpoints incluem:
- Exemplos de request/response
- Códigos de erro detalhados
- Validações automáticas
- Metadados ricos

---

## 🚀 **Deploy e Produção**

### **⚙️ Variáveis de Ambiente (Produção)**

**Variáveis Obrigatórias:**
```bash
DATABASE_URL=postgresql://user:password@host:5432/intelectus_db
SECRET_KEY=chave-super-secreta-256-bits-aleatoria
CORS_ORIGINS=https://app.intelectus.com.br,https://admin.intelectus.com.br
DEBUG=False
```

**Variáveis Opcionais:**
```bash
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
PROJECT_NAME=Intelectus API
VERSION=0.1.0
RPI_BASE_URL=https://revistas.inpi.gov.br
```

**⚠️ CRÍTICO:** 
- `SECRET_KEY` deve ser uma string aleatória de 256 bits
- `CORS_ORIGINS` é obrigatório em produção (sem ele, todas as origens são bloqueadas)
- `DEBUG=False` em produção (segurança)

### **🐳 Deploy com Docker**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **🔧 Comando de Produção**
```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar .env com variáveis de produção (obrigatório)
# DATABASE_URL, SECRET_KEY, CORS_ORIGINS, DEBUG=False

# 3. Aplicar migrations
python cli.py db upgrade

# 4. Iniciar servidor produção
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Ou com gunicorn (recomendado para produção)
# Instalar: pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**⚠️ Checklist de Produção:**
- [ ] `DEBUG=False` no .env
- [ ] `CORS_ORIGINS` configurado com domínios específicos
- [ ] `SECRET_KEY` forte e aleatória
- [ ] `DATABASE_URL` apontando para banco de produção
- [ ] Migrations aplicadas
- [ ] Rate limiting funcionando (slowapi instalado)

---

## 🤝 **Contribuição**

### **🔧 Setup para Desenvolvimento**
```bash
# 1. Fork e clone
git clone <seu-fork>
cd Intelectus-Api

# 2. Setup ambiente
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar .env (ver seção "Configurar Variáveis de Ambiente")
# DATABASE_URL=postgresql://admin:Inicio@123@localhost:5432/intelectus_db
# SECRET_KEY=sua-chave-secreta-aqui
# DEBUG=True

# 5. Configurar banco local
docker-compose up -d  # Ou configurar PostgreSQL manualmente
python cli.py dev test-connection
python cli.py db upgrade

# 6. Criar admin para testes
python cli.py dev create-admin

# 7. Iniciar desenvolvimento
python cli.py server run
# API disponível em http://localhost:8000/docs
```

### **📋 Padrões de Código**
- **FastAPI** - endpoints com type hints
- **Pydantic v2** - validação de dados
- **SQLAlchemy** - ORM com relacionamentos
- **Alembic** - migrations versionadas
- **JWT** - autenticação stateless

---

## 📊 **Funcionalidades Implementadas**

### ✅ **Core Completo**
- [x] API REST com FastAPI
- [x] Autenticação JWT + bcrypt
- [x] CRUD completo para todas entidades
- [x] Relacionamentos N:N com auditoria
- [x] Sistema de permissões granular
- [x] Migrations profissionais
- [x] CLI administrativo
- [x] Documentação Swagger

### ✅ **Recursos Avançados**  
- [x] Membership com 3 tabelas
- [x] Auditoria completa (quem/quando/por que)
- [x] Soft/hard delete
- [x] Estatísticas e dashboards
- [x] Validação automática
- [x] Error handling robusto
- [x] Middleware de segurança

### 🎯 **Opcionais para Futuro**
- [ ] Cache com Redis
- [ ] Notificações push/email
- [x] Rate limiting (✅ implementado)
- [ ] Logs centralizados
- [ ] Métricas com Prometheus
- [ ] 2FA/MFA
- [ ] OAuth2 providers

---

## 📈 **Status do Projeto**

### 🎉 **100% Funcional**
O sistema está **completo e pronto** para desenvolvimento e produção:

- ✅ **Todas as funcionalidades** implementadas
- ✅ **Código testado** e funcionando
- ✅ **Documentação completa**
- ✅ **CLI para produtividade**
- ✅ **Migrations profissionais**
- ✅ **Arquitetura escalável**

### 🚀 **Começar Agora**
```bash
# Clone, configure e execute em 2 minutos
git clone <repo> && cd Intelectus-Api
python cli.py dev test-connection
python cli.py db upgrade  
python cli.py server run

# 🎯 API rodando em http://localhost:8000/docs
```

---

## 📞 **Suporte**

### **🐛 Issues**
- Reporte bugs via GitHub Issues
- Inclua logs e contexto
- Use labels apropriados

### **💡 Feature Requests**  
- Sugira melhorias via GitHub Issues
- Descreva caso de uso
- Considere implementar e enviar PR

### **📚 Documentação**
- Swagger/OpenAPI para referência da API
- CLI-GUIDE.md para comandos administrativos
- MIGRATIONS.md para gestão do banco

---

**🎯 Intelectus API - Sistema robusto e profissional para propriedade intelectual**

![Made with FastAPI](https://img.shields.io/badge/Made%20with-FastAPI-green.svg)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue.svg)  
![Alembic](https://img.shields.io/badge/Migrations-Alembic-red.svg)
![Rich CLI](https://img.shields.io/badge/CLI-Rich-purple.svg) 