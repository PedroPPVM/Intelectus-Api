# 🗄️ Migrations com Alembic - Intelectus API

Este documento explica como usar o **Alembic** para gerenciar as mudanças do banco de dados no projeto Intelectus.

## 📋 **Comandos Principais:**

### **1. 🔍 Ver Status Atual:**
```bash
# Verificar qual migration está aplicada
alembic current

# Ver histórico de migrations
alembic history --verbose

# Ver migrations pendentes
alembic show head
```

### **2. 🆕 Criar Nova Migration:**
```bash
# Criar migration automática (recomendado)
alembic revision --autogenerate -m "Adicionar campo email_verified na tabela user"

# Criar migration manual (vazia)  
alembic revision -m "Adicionar índice customizado"
```

### **3. ⬆️ Aplicar Migrations:**
```bash
# Aplicar todas as migrations pendentes
alembic upgrade head

# Aplicar até uma migration específica
alembic upgrade 338f06ee323a

# Aplicar próxima migration apenas
alembic upgrade +1
```

### **4. ⬇️ Reverter Migrations:**
```bash
# Reverter uma migration
alembic downgrade -1

# Reverter para migration específica
alembic downgrade 338f06ee323a

# Reverter todas (CUIDADO!)
alembic downgrade base
```

---

## 🛠️ **Workflow Recomendado:**

### **Para Mudanças nos Modelos:**

1. **Modificar o modelo** em `app/models/`
2. **Criar migration automática:**
   ```bash
   alembic revision --autogenerate -m "Descrição da mudança"
   ```
3. **Revisar o arquivo** de migration gerado em `alembic/versions/`
4. **Aplicar a migration:**
   ```bash
   alembic upgrade head
   ```

### **Exemplo Prático:**
```python
# 1. Modificar modelo (app/models/user.py)
class User(Base):
    # ... campos existentes ...
    email_verified = Column(Boolean, default=False)  # 🆕 NOVO CAMPO
```

```bash
# 2. Gerar migration
alembic revision --autogenerate -m "Add email_verified field to users"

# 3. Aplicar migration  
alembic upgrade head
```

---

## 🔧 **Estrutura de Arquivos:**

```
Intelectus-Api/
├── alembic/                    # Pasta do Alembic
│   ├── versions/               # 📁 Migrations
│   │   └── 338f06ee323a_*.py  # Migration files
│   ├── env.py                 # ⚙️ Configuração
│   └── script.py.mako         # 🎨 Template
├── alembic.ini                # 📋 Configuração principal
└── app/
    └── models/                # 🏗️ Modelos SQLAlchemy
```

---

## ✅ **Boas Práticas:**

### **📝 Nomes de Migration:**
```bash
# ✅ BOM - Descritivo e claro
alembic revision --autogenerate -m "Add membership audit tables"
alembic revision --autogenerate -m "Remove deprecated user_company endpoints" 
alembic revision --autogenerate -m "Add process_type index for performance"

# ❌ RUIM - Vago demais
alembic revision --autogenerate -m "update"
alembic revision --autogenerate -m "fix"
```

### **🔍 Sempre Revisar Migrations:**
- ✅ **Conferir** o arquivo gerado antes de aplicar
- ✅ **Testar** em ambiente de desenvolvimento primeiro  
- ✅ **Backup** antes de aplicar em produção
- ✅ **Documentar** mudanças complexas nos comentários

### **🏷️ Versionamento:**
```bash
# Para releases importantes, criar tags
git tag v1.0.0-migration-baseline
git tag v1.1.0-membership-system
```

---

## 🚨 **Comandos de Emergência:**

### **Migration Quebrada:**
```bash
# 1. Reverter para migration anterior
alembic downgrade -1

# 2. Editar migration problemática
# 3. Tentar aplicar novamente
alembic upgrade head
```

### **Banco Dessincronizado:**
```bash
# 1. Ver diferenças
alembic revision --autogenerate -m "Sync database state"

# 2. Se necessário, forçar stamp
alembic stamp head
```

### **Reset Completo (CUIDADO!):**
```bash
# APENAS PARA DESENVOLVIMENTO - PERDE TODOS OS DADOS!
# 1. Dropar todas as tabelas manualmente
# 2. Recriar do zero
alembic upgrade head
```

---

## 📊 **Status do Projeto:**

### **✅ Configuração Atual:**
- ✅ **Alembic configurado** e funcionando
- ✅ **Migration baseline** criada (`338f06ee323a`)
- ✅ **Todas as tabelas** mapeadas (User, Company, Process, Alert, Membership*)
- ✅ **Autogenerate** habilitado
- ✅ **Comparação de tipos** e defaults ativa

### **🏗️ Tabelas Gerenciadas:**
- ✅ `user` - Usuários do sistema
- ✅ `company` - Empresas/organizações  
- ✅ `process` - Processos de propriedade intelectual
- ✅ `alert` - Alertas e notificações
- ✅ `user_company_association` - Relacionamento N:N legacy
- ✅ `user_company_membership` - **NOVO** Sistema avançado de membership
- ✅ `membership_history` - **NOVO** Auditoria de mudanças
- ✅ `user_company_permission` - **NOVO** Permissões granulares

---

## 🎯 **Comandos Úteis para Desenvolvimento:**

```bash
# Status rápido
alembic current && alembic show head

# Criar e aplicar de uma vez (CUIDADO!)
alembic revision --autogenerate -m "Quick fix" && alembic upgrade head

# Ver SQL que será executado (sem aplicar)
alembic upgrade head --sql

# Comparar estado atual com modelos
alembic revision --autogenerate -m "Check differences" --splice
```

---

**🎉 Alembic configurado com sucesso!** Agora você tem controle total sobre a evolução do banco de dados. 🚀 