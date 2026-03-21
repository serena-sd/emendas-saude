from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/")
def home():
    return {"status": "API profissional rodando"}


@app.get("/proposta/{numero}")
def buscar_proposta(numero: str):

    url = "https://consultafns.saude.gov.br/recursos/proposta/consultar"

    params = {
        "ano": "2026",
        "coEsfera": "3",
        "coMunicipioIbge": "430545",  # CIDREIRA
        "count": "10",
        "nuProposta": numero
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return {"erro": "Falha ao consultar FNS"}

    data = response.json()

    try:
        item = data["resultado"]["itensPagina"][0]

        return {
            "numero_proposta": numero,
            "tipo_proposta": item.get("coTipoProposta"),
            "tipo_recurso": item.get("dsTipoRecurso"),
            "valor": item.get("vlProposta"),
            "valor_pago": item.get("vlPago"),
            "processo": item.get("nuProcesso"),
            "tem_pagamento": len(item.get("pagamentos", [])) > 0,
            "processo_constituido": item.get("constituidoProcesso")
        }

    except:
        return {"erro": "Proposta não encontrada ou estrutura inesperada"}
