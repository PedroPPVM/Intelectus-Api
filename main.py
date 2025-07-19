from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Project": "Intelectus", "Status": "Iniciando o desenvolvimento!"}