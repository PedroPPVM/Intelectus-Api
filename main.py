"""
Ponto de entrada principal da aplicação Intelectus API.
Este arquivo serve como bridge para a aplicação FastAPI dentro do diretório app/.
"""
from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )