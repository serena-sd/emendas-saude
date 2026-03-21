from fastapi import FastAPI
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re
import time

app = FastAPI()

def extrair(texto: str, inicio: str, fim: str | None = None):
    try:
        if inicio not in texto:
            return None
        parte = texto.split(inicio, 1)[1]
        if fim and fim in parte:
            parte = parte.split(fim, 1)[0]
        return parte.strip()
    except Exception:
        return None

@app.get("/")
def home():
    return {"status": "API profissional rodando"}

@app.get("/proposta/{numero}")
def buscar_proposta(numero: str):
    driver = None
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = "/usr/bin/chromium"

        driver = webdriver.Chrome(options=options)

        url = f"https://consultafns.saude.gov.br/#/proposta/{numero}/detalhe"
        driver.get(url)
        time.sleep(6)

        texto = driver.find_element(By.TAG_NAME, "body").text

        resultado = {
            "numero_proposta": numero,
            "estado": extrair(texto, "Estado", "Município"),
            "municipio": extrair(texto, "Município", "Entidade"),
            "entidade": extrair(texto, "Entidade", "CNPJ"),
            "cnpj": extrair(texto, "CNPJ", "Dados da Proposta"),
            "tipo_proposta": extrair(texto, "Tipo de Proposta", "Ano"),
            "ano": extrair(texto, "Ano", "Valor da Proposta"),
            "valor_proposta": extrair(texto, "Valor da Proposta", "Nº Portaria"),
            "valor_total_empenho": extrair(texto, "Valor Total de Empenho", "Valor a Pagar"),
            "valor_a_pagar": extrair(texto, "Valor a Pagar", "Dados da Situação da Proposta"),
            "situacao_atual": extrair(texto, "Situação Atual da Proposta", "Data da Última Atualização da Proposta"),
            "data_ultima_atualizacao": extrair(texto, "Data da Última Atualização da Proposta", "Principais etapas da proposta"),
            "partido": extrair(texto, "Partido", "Nome Parlamentar"),
            "parlamentar": extrair(texto, "Nome Parlamentar", "Nº da Emenda"),
            "numero_emenda": extrair(texto, "Nº da Emenda", "Ano"),
            "valor_emenda": extrair(texto, "Valor da Emenda", "Não foi constituído processo para essa proposta.")
        }

        return resultado

    except Exception as e:
        return {"erro": str(e)}

    finally:
        if driver:
            driver.quit()
