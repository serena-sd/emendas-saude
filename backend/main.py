
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os

app = FastAPI()

# Permitir acesso do frontend (GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY")

@app.get("/")
def home():
    return {"status": "API rodando"}

@app.get("/emenda/{numero}")
def buscar_emenda(numero: str):
    url = f"https://api.portaldatransparencia.gov.br/api-de-dados/emendas?codigoEmenda={numero}"

    headers = {
        "chave-api-dados": API_KEY
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {"erro": "Falha ao buscar dados"}

    return response.json()
