#!/usr/bin/env python3
"""
🎯 Intelectus CLI - Comandos administrativos para o projeto

Este CLI centraliza todas as operações frequentes:
- Migrations e banco de dados
- Comandos de desenvolvimento  
- Gestão de usuários e dados
- Manutenção e deploy

Uso: python cli.py [COMANDO] [OPÇÕES]
"""

import os
import sys
import subprocess
from typing import Optional
from pathlib import Path

import typer
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Adicionar o projeto ao path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar Rich console
console = Console()
app = typer.Typer(
    name="intelectus",
    help="🎯 CLI administrativo do projeto Intelectus",
    add_completion=False,
    rich_markup_mode="rich"
)

# Sub-aplicações para organizar comandos
db_app = typer.Typer(name="db", help="🗄️  Comandos de banco de dados e migrations")
dev_app = typer.Typer(name="dev", help="🛠️  Comandos de desenvolvimento")  
server_app = typer.Typer(name="server", help="🚀 Comandos do servidor")
membership_app = typer.Typer(name="membership", help="👥 Comandos de membership")

app.add_typer(db_app)
app.add_typer(dev_app)
app.add_typer(server_app)
app.add_typer(membership_app)


# =================== COMANDOS DE BANCO ===================

@db_app.command("status")
def db_status():
    """🔍 Ver status atual das migrations"""
    console.print("🔍 [bold blue]Verificando status das migrations...[/bold blue]")
    
    try:
        result = subprocess.run(["alembic", "current"], 
                              capture_output=True, text=True, check=True)
        current_migration = result.stdout.strip()
        
        result_head = subprocess.run(["alembic", "show", "head"], 
                                   capture_output=True, text=True, check=True)
        head_migration = result_head.stdout.strip()
        
        table = Table(title="📊 Status das Migrations")
        table.add_column("Item", style="cyan")
        table.add_column("Valor", style="green")
        
        table.add_row("Migration Atual", current_migration)
        table.add_row("Migration HEAD", head_migration)
        
        if current_migration == head_migration:
            table.add_row("Status", "✅ Atualizado")
        else:
            table.add_row("Status", "⚠️  Migrations pendentes")
        
        console.print(table)
        
    except subprocess.CalledProcessError as e:
        console.print(f"❌ [red]Erro ao verificar status: {e}[/red]")
        raise typer.Exit(1)


@db_app.command("upgrade")
def db_upgrade(target: str = "head"):
    """⬆️ Aplicar migrations"""
    console.print(f"⬆️ [bold green]Aplicando migrations até: {target}[/bold green]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Aplicando migrations...", total=None)
        
        try:
            subprocess.run(["alembic", "upgrade", target], check=True)
            progress.update(task, description="✅ Migrations aplicadas com sucesso!")
            
        except subprocess.CalledProcessError as e:
            console.print(f"❌ [red]Erro ao aplicar migrations: {e}[/red]")
            raise typer.Exit(1)


@db_app.command("downgrade")
def db_downgrade(target: str = "-1"):
    """⬇️ Reverter migrations"""
    if not typer.confirm(f"⚠️ Tem certeza que deseja reverter para '{target}'?"):
        console.print("❌ Operação cancelada")
        return
        
    console.print(f"⬇️ [bold yellow]Revertendo migrations para: {target}[/bold yellow]")
    
    try:
        subprocess.run(["alembic", "downgrade", target], check=True)
        console.print("✅ [green]Migration revertida com sucesso![/green]")
        
    except subprocess.CalledProcessError as e:
        console.print(f"❌ [red]Erro ao reverter migration: {e}[/red]")
        raise typer.Exit(1)


@db_app.command("create")
def db_create_migration(message: str):
    """📝 Criar nova migration"""
    console.print(f"📝 [bold blue]Criando migration: {message}[/bold blue]")
    
    try:
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", message], check=True)
        console.print("✅ [green]Migration criada com sucesso![/green]")
        console.print("💡 [dim]Lembre-se de revisar o arquivo gerado antes de aplicar[/dim]")
        
    except subprocess.CalledProcessError as e:
        console.print(f"❌ [red]Erro ao criar migration: {e}[/red]")
        raise typer.Exit(1)


@db_app.command("history")
def db_history():
    """📚 Ver histórico de migrations"""
    console.print("📚 [bold blue]Histórico de migrations:[/bold blue]")
    
    try:
        subprocess.run(["alembic", "history", "--verbose"], check=True)
        
    except subprocess.CalledProcessError as e:
        console.print(f"❌ [red]Erro ao buscar histórico: {e}[/red]")
        raise typer.Exit(1)


@db_app.command("reset")
def db_reset():
    """🔄 Reset completo do banco (CUIDADO!)"""
    console.print("⚠️ [bold red]ATENÇÃO: Esta operação apagará TODOS OS DADOS![/bold red]")
    
    if not typer.confirm("Tem certeza que deseja continuar?"):
        console.print("❌ Operação cancelada")
        return
        
    if not typer.confirm("CONFIRMAÇÃO FINAL: Apagar todos os dados?"):
        console.print("❌ Operação cancelada")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Resetando banco...", total=None)
        
        try:
            # Importar SQLAlchemy e TODOS os modelos para criar tabelas
            from app.db.session import engine
            from app.db.base_class import Base
            from sqlalchemy import text
            
            # Importar todos os modelos para registrar no metadata
            from app.models.user import User
            from app.models.company import Company
            from app.models.process import Process
            from app.models.alert import Alert
            from app.models.membership import UserCompanyMembership, MembershipHistory, UserCompanyPermission
            
            # Dropar todas as tabelas (incluindo dados)
            progress.update(task, description="Dropando todas as tabelas...")
            with engine.connect() as conn:
                # Dropar todas as tabelas do schema public (incluindo alembic_version)
                conn.execute(text("DROP SCHEMA public CASCADE;"))
                conn.execute(text("CREATE SCHEMA public;"))
                # Grant permissions back to public schema
                conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
                conn.commit()
            
            # Criar todas as tabelas usando SQLAlchemy
            progress.update(task, description="Criando todas as tabelas...")
            Base.metadata.create_all(bind=engine)
            
            # Marcar migrations como aplicadas
            progress.update(task, description="Marcando migrations como aplicadas...")
            subprocess.run(["alembic", "stamp", "head"], check=True)
            
            progress.update(task, description="✅ Reset completo realizado!")
            console.print("🎉 [green]Banco completamente resetado com sucesso![/green]")
            console.print("ℹ️ [cyan]Todas as tabelas e dados foram apagados e recriados.[/cyan]")
            
        except (subprocess.CalledProcessError, Exception) as e:
            console.print(f"❌ [red]Erro durante reset: {e}[/red]")
            console.print("💡 [yellow]Verifique se o banco de dados está acessível e as credenciais estão corretas.[/yellow]")
            raise typer.Exit(1)


# =================== COMANDOS DE DESENVOLVIMENTO ===================

@dev_app.command("create-admin")
def dev_create_admin(
    email: str = typer.Option(..., prompt="Email do admin"),
    password: str = typer.Option(..., prompt=True, hide_input=True),
    name: str = typer.Option(..., prompt="Nome completo")
):
    """👑 Criar usuário administrador"""
    console.print("👑 [bold blue]Criando usuário administrador...[/bold blue]")
    
    try:
        # Importar aqui para evitar problemas de import
        from app.db.session import get_db_session
        from app.models.user import User
        from app.security.auth import create_password_hash
        import uuid
        
        db = get_db_session()
        try:
            # Verificar se já existe
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                console.print(f"❌ [red]Usuário {email} já existe[/red]")
                return
            
            # Criar usuário
            admin_user = User(
                id=uuid.uuid4(),
                email=email,
                full_name=name,
                hashed_password=create_password_hash(password),
                is_active=True,
                is_superuser=True
            )
            
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            console.print(f"✅ [green]Administrador criado: {email}[/green]")
        finally:
            db.close()
            
    except Exception as e:
        console.print(f"❌ [red]Erro ao criar administrador: {e}[/red]")
        raise typer.Exit(1)


@dev_app.command("test-connection")
def dev_test_connection():
    """🔌 Testar conexão com o banco"""
    console.print("🔌 [bold blue]Testando conexão com banco...[/bold blue]")
    
    try:
        from app.db.session import get_db_session
        from sqlalchemy import text
        
        db = get_db_session()
        try:
            result = db.execute(text("SELECT 1 as test")).fetchone()
            if result and result[0] == 1:
                console.print("✅ [green]Conexão com banco funcionando![/green]")
            else:
                console.print("❌ [red]Problema na conexão[/red]")
        finally:
            db.close()
                
    except Exception as e:
        console.print(f"❌ [red]Erro de conexão: {e}[/red]")
        raise typer.Exit(1)


# =================== COMANDOS DO SERVIDOR ===================

@server_app.command("run")
def server_run(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = True,
    workers: int = 1
):
    """🚀 Iniciar servidor de desenvolvimento"""
    console.print(f"🚀 [bold green]Iniciando servidor em http://{host}:{port}[/bold green]")
    
    cmd = [
        "uvicorn", "app.main:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    if workers > 1:
        cmd.extend(["--workers", str(workers)])
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n👋 [yellow]Servidor finalizado[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ [red]Erro ao iniciar servidor: {e}[/red]")
        raise typer.Exit(1)


@server_app.command("test")
def server_test():
    """🧪 Executar testes da API"""
    console.print("🧪 [bold blue]Executando testes...[/bold blue]")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/docs")
        
        if response.status_code == 200:
            console.print("✅ [green]API respondendo corretamente![/green]")
        else:
            console.print(f"⚠️ [yellow]API respondeu com status {response.status_code}[/yellow]")
            
    except Exception as e:
        console.print(f"❌ [red]Erro ao testar API: {e}[/red]")
        console.print("💡 [dim]Certifique-se que o servidor está rodando[/dim]")


# =================== COMANDOS DE MEMBERSHIP ===================

@membership_app.command("stats")
def membership_stats(company_id: Optional[str] = None):
    """📊 Ver estatísticas de membership"""
    console.print("📊 [bold blue]Estatísticas de Membership[/bold blue]")
    
    try:
        from app.db.session import get_db_session
        from app.services.membership_service import membership_service
        from uuid import UUID
        
        db = get_db_session()
        try:
            if company_id:
                stats = membership_service.get_membership_stats(db, UUID(company_id))
                
                table = Table(title=f"Estatísticas - Company: {company_id}")
                table.add_column("Métrica", style="cyan")
                table.add_column("Valor", style="green")
                
                table.add_row("Total de Membros", str(stats.total_members))
                table.add_row("Membros Ativos", str(stats.active_members))
                table.add_row("Membros Inativos", str(stats.inactive_members))
                table.add_row("Mudanças Recentes", str(stats.recent_changes))
                
                for role, count in stats.members_by_role.items():
                    table.add_row(f"Role: {role}", str(count))
                
                console.print(table)
            else:
                console.print("💡 [dim]Use: --company-id UUID para ver stats específicas[/dim]")
        finally:
            db.close()
                
    except Exception as e:
        console.print(f"❌ [red]Erro ao buscar estatísticas: {e}[/red]")


# =================== COMANDO PRINCIPAL ===================

@app.command("info")
def info():
    """ℹ️ Informações sobre o projeto"""
    panel = Panel.fit(
        """[bold blue]🎯 Intelectus API[/bold blue]

[green]✅ Status:[/green] Sistema funcionando
[green]✅ Database:[/green] PostgreSQL com migrations
[green]✅ Authentication:[/green] JWT + bcrypt
[green]✅ Membership:[/green] Sistema avançado com auditoria

[yellow]📚 Comandos Disponíveis:[/yellow]
• [cyan]db[/cyan]         - Migrations e banco de dados
• [cyan]dev[/cyan]        - Ferramentas de desenvolvimento  
• [cyan]server[/cyan]     - Gerenciar servidor
• [cyan]membership[/cyan] - Sistema de membership

[dim]Use --help em qualquer comando para mais detalhes[/dim]
        """,
        title="🎯 Intelectus CLI",
        border_style="blue"
    )
    console.print(panel)


if __name__ == "__main__":
    app() 