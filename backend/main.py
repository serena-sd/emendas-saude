from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os

app = FastAPI(title="API Emendas Saúde")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY", "").strip()

@app.get("/")
def home():
    return {
        "status": "API rodando",
        "rotas": [
            "/emenda/{numero}",
            "/proposta/{numero}"
        ]
    }

@app.get("/emenda/{numero}")
def buscar_emenda(numero: str):
    """
    Busca emenda parlamentar na API do Portal da Transparência.
    Útil para localizar dados gerais da emenda.
    """
    if not API_KEY:
        return {"erro": "API_KEY não configurada no servidor"}

    url = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"

    headers = {
        "chave-api-dados": API_KEY,
        "accept": "application/json"
    }

    params = {
        "numeroEmenda": numero
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
    except Exception as e:
        return {"erro": f"Falha de conexão com Portal da Transparência: {str(e)}"}

    if response.status_code != 200:
        return {
            "erro": "Falha ao buscar dados da emenda",
            "status_code": response.status_code,
            "resposta": response.text
        }

    try:
        data = response.json()
    except Exception:
        return {
            "erro": "Resposta não veio em JSON",
            "status_code": response.status_code,
            "resposta": response.text
        }

    return {
        "fonte": "Portal da Transparência",
        "tipo_consulta": "emenda",
        "numero_pesquisado": numero,
        "quantidade_resultados": len(data) if isinstance(data, list) else 0,
        "dados": data
    }

@app.get("/proposta/{numero}")
def buscar_proposta(numero: str):
    """
    Monta a URL pública da proposta FNS.
    Observação: esta versão não faz scraping automático.
    Ela devolve o link e a classificação inicial da busca.
    """
    numero = str(numero).strip()

    url_publica = f"https://consultafns.saude.gov.br/#/proposta/{numero}/detalhe"

    tipo_sugerido = "proposta_fns"
    observacao = (
        "Para propostas FNS/FAF, esta é a fonte prioritária para conferir "
        "município, entidade, tipo da proposta, valor, situação, parlamentar e nº da emenda."
    )

    return {
        "fonte": "Consulta FNS",
        "tipo_consulta": tipo_sugerido,
        "numero_pesquisado": numero,
        "url_publica": url_publica,
        "observacao": observacao
    }
