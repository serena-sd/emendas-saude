from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup

app = FastAPI()

@app.get("/")
def home():
    return {"status": "API rodando"}

@app.get("/proposta/{numero}")
def buscar_proposta(numero: str):
    try:
        url = f"https://consultafns.saude.gov.br/#/proposta/{numero}/detalhe"

        response = requests.get(url)

        if response.status_code != 200:
            return {"erro": "Não conseguiu acessar o site"}

        soup = BeautifulSoup(response.text, "html.parser")

        texto = soup.get_text()

        return {
            "numero_proposta": numero,
            "dados_brutos": texto[:2000]  # só pra testar
        }

    except Exception as e:
        return {"erro": str(e)}
