from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup

app = FastAPI()

@app.get("/")
def home():
    return {"status": "API rodando"}

@app.get("/proposta/{numero}")
def buscar_proposta(numero: str):
    url = f"https://consultafns.saude.gov.br/#/proposta/{numero}/detalhe"

    try:
        # tentativa de pegar conteúdo
        response = requests.get(url, timeout=30)
    except Exception as e:
        return {"erro": f"Falha de conexão: {str(e)}"}

    # ⚠️ FNS é dinâmico → HTML vem vazio
    if response.status_code != 200:
        return {"erro": "Não foi possível acessar proposta"}

    # Aqui já avisamos que precisa melhorar (fase 2)
    return {
        "numero_proposta": numero,
        "status": "detectada",
        "mensagem": "FNS usa carregamento dinâmico - próxima etapa é integração real",
        "url": url
    }
