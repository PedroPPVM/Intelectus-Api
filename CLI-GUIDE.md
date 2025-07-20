# 🎯 Intelectus CLI - Guia Completo

O **Intelectus CLI** centraliza todas as operações frequentes do projeto em uma interface de linha de comando intuitiva e poderosa.

## 🚀 **Como Usar:**

```bash
# Comando base
python cli.py [CATEGORIA] [COMANDO] [OPÇÕES]

# Ou diretamente (se executável)
./cli.py [CATEGORIA] [COMANDO] [OPÇÕES]
```

---

## 📋 **Categorias de Comandos:**

### **1. 🗄️ `db` - Banco de Dados e Migrations**

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `status` | 🔍 Ver status atual das migrations | `python cli.py db status` |
| `upgrade` | ⬆️ Aplicar migrations | `python cli.py db upgrade` |
| `downgrade` | ⬇️ Reverter migrations | `python cli.py db downgrade -1` |
| `create` | 📝 Criar nova migration | `python cli.py db create "Add user avatar"` |
| `history` | 📚 Ver histórico completo | `python cli.py db history` |
| `reset` | 🔄 Reset completo (CUIDADO!) | `python cli.py db reset` |

**Exemplos detalhados:**
```bash
# Ver status das migrations
python cli.py db status

# Aplicar todas as migrations pendentes
python cli.py db upgrade

# Aplicar até migration específica
python cli.py db upgrade 338f06ee323a

# Reverter 2 migrations
python cli.py db downgrade -2

# Criar migration para nova feature
python cli.py db create "Add email verification system"
```

### **2. 🛠️ `dev` - Desenvolvimento**

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `create-admin` | 👑 Criar usuário administrador | `python cli.py dev create-admin` |
| `test-connection` | 🔌 Testar conexão com banco | `python cli.py dev test-connection` |

**Exemplos detalhados:**
```bash
# Criar administrador interativo (vai pedir dados)
python cli.py dev create-admin

# Testar se o banco está respondendo
python cli.py dev test-connection
```

### **3. 🚀 `server` - Servidor**

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `run` | 🚀 Iniciar servidor de desenvolvimento | `python cli.py server run` |
| `test` | 🧪 Testar se API está funcionando | `python cli.py server test` |

**Exemplos detalhados:**
```bash
# Iniciar servidor padrão (localhost:8000)
python cli.py server run

# Iniciar em porta específica
python cli.py server run --port 3000

# Iniciar sem reload automático
python cli.py server run --no-reload

# Iniciar com múltiplos workers
python cli.py server run --workers 4
```

### **4. 👥 `membership` - Sistema de Membership**

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `stats` | 📊 Ver estatísticas de membership | `python cli.py membership stats --company-id UUID` |

**Exemplos detalhados:**
```bash
# Ver estatísticas de uma empresa específica
python cli.py membership stats --company-id 987fcdeb-51a2-43d1-b123-456789abcdef
```

### **5. ℹ️ Comando Geral**

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `info` | ℹ️ Informações sobre o projeto | `python cli.py info` |

---

## 🎨 **Recursos Visuais:**

O CLI usa **Rich** para outputs bonitos e informativos:

- ✅ **Cores** para status (verde=sucesso, vermelho=erro, amarelo=aviso)
- 📊 **Tabelas** organizadas para informações
- 🔄 **Progress bars** para operações longas  
- 🎯 **Painéis** com bordas para destaque
- 🔍 **Confirmações** interativas para operações perigosas

---

## 💡 **Workflows Comuns:**

### **🔄 Workflow de Migration:**
```bash
# 1. Ver status atual
python cli.py db status

# 2. Criar migration após mudança no modelo
python cli.py db create "Add user profile fields"

# 3. Aplicar migration
python cli.py db upgrade

# 4. Verificar se aplicou
python cli.py db status
```

### **🚀 Workflow de Desenvolvimento:**
```bash
# 1. Testar conexão
python cli.py dev test-connection

# 2. Aplicar migrations mais recentes
python cli.py db upgrade

# 3. Criar admin se necessário
python cli.py dev create-admin

# 4. Iniciar servidor
python cli.py server run
```

### **📊 Workflow de Monitoramento:**
```bash
# Ver informações do projeto
python cli.py info

# Status do banco
python cli.py db status

# Testar API
python cli.py server test

# Ver stats de membership
python cli.py membership stats --company-id UUID
```

---

## ⚙️ **Configuração Avançada:**

### **Variáveis de Ambiente:**
O CLI usa as mesmas configurações do projeto:
- `DATABASE_URL` - String de conexão PostgreSQL
- `SECRET_KEY` - Chave para JWT
- `.env` - Arquivo de configuração

### **Logs e Debugging:**
```bash
# Para ver logs detalhados do SQLAlchemy
export SQLALCHEMY_LOG_LEVEL=INFO
python cli.py dev test-connection
```

---

## 🛡️ **Comandos Perigosos:**

### **⚠️ Comandos que Exigem Confirmação:**

1. **`db reset`** - Apaga TODOS os dados
   ```bash
   python cli.py db reset
   # ⚠️  ATENÇÃO: Esta operação apagará TODOS OS DADOS!
   # Tem certeza que deseja continuar? [y/N]: 
   ```

2. **`db downgrade`** - Reverte migrations
   ```bash
   python cli.py db downgrade -1
   # ⚠️ Tem certeza que deseja reverter para '-1'? [y/N]:
   ```

---

## 🔧 **Personalização e Extensão:**

### **Adicionar Novos Comandos:**
1. Editar `cli.py`
2. Criar nova função com decorador `@app.command()`
3. Usar `typer.Option()` para parâmetros
4. Implementar lógica com feedback via `console.print()`

### **Exemplo de Novo Comando:**
```python
@dev_app.command("backup")
def dev_backup(output_file: str = "backup.sql"):
    """💾 Criar backup do banco"""
    console.print(f"🔄 [blue]Criando backup: {output_file}[/blue]")
    # Lógica do backup aqui
    console.print("✅ [green]Backup criado com sucesso![/green]")
```

---

## 📈 **Comparação com Comandos Manuais:**

| Operação | Comando Manual | CLI Intelectus | Benefício |
|----------|---------------|-----------------|-----------|
| Status migrations | `alembic current` | `./cli.py db status` | 📊 Tabela organizada |
| Criar migration | `alembic revision --autogenerate -m "msg"` | `./cli.py db create "msg"` | 📝 Mais simples |
| Aplicar migrations | `alembic upgrade head` | `./cli.py db upgrade` | 🔄 Progress bar |
| Iniciar servidor | `uvicorn app.main:app --reload` | `./cli.py server run` | 🚀 Configurável |
| Criar admin | Script customizado | `./cli.py dev create-admin` | 👑 Interativo |

---

## 🎯 **Vantagens do CLI:**

- ✅ **Centralização** - Todos os comandos em um lugar
- ✅ **Consistência** - Interface uniforme para tudo
- ✅ **Feedback visual** - Outputs bonitos e informativos
- ✅ **Segurança** - Confirmações para operações perigosas
- ✅ **Produtividade** - Workflows otimizados
- ✅ **Extensibilidade** - Fácil adicionar novos comandos

---

**🎉 O CLI torna o desenvolvimento muito mais ágil e profissional!** 

Use `python cli.py --help` para explorar todos os comandos disponíveis. 