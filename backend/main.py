from fastapi import FastAPI
import requests
import os

app = FastAPI()

API_KEY = os.getenv("API_KEY")

@app.get("/")
def home():
    return {"status": "API rodando"}

@app.get("/emenda/{numero}")
def buscar_emenda(numero: str):
    url = f"https://api.portaldatransparencia.gov.br/api-de-dados/emendas?numeroEmenda={numero}"

    headers = {
        "chave-api-dados": API_KEY
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {"erro": "Erro ao buscar dados", "status": response.status_code}

    return response.json()
