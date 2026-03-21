from fastapi import FastAPI
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

app = FastAPI()

@app.get("/")
def home():
    return {"status": "API profissional rodando"}

@app.get("/proposta/{numero}")
def buscar_proposta(numero: str):
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)

        url = f"https://consultafns.saude.gov.br/#/proposta/{numero}/detalhe"
        driver.get(url)

        time.sleep(5)  # aguarda carregar

        dados = {}

        try:
            dados["proposta"] = numero
            dados["titulo"] = driver.find_element(By.TAG_NAME, "body").text[:500]
        except:
            dados["erro"] = "Não conseguiu capturar dados"

        driver.quit()

        return dados

    except Exception as e:
        return {"erro": str(e)}
