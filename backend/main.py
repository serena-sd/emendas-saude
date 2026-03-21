from fastapi import FastAPI
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

app = FastAPI()


def limpar(valor):
    if valor is None:
        return None
    valor = valor.strip()
    return valor if valor else None


def extrair_bloco(texto: str, inicio: str, fim: str | None = None):
    try:
        if inicio not in texto:
            return None
        parte = texto.split(inicio, 1)[1]
        if fim and fim in parte:
            parte = parte.split(fim, 1)[0]
        return limpar(parte)
    except Exception:
        return None


def extrair_campo_regex(texto: str, padrao: str):
    m = re.search(padrao, texto, flags=re.DOTALL)
    if not m:
        return None
    return limpar(m.group(1))


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

        # espera a página realmente carregar
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Dados da Proposta')]")
            )
        )

        texto = driver.find_element(By.TAG_NAME, "body").text
        texto = re.sub(r"\r", "\n", texto)
        texto = re.sub(r"\n+", "\n", texto).strip()

        # extrações principais por regex, mais robustas
        estado = extrair_campo_regex(texto, r"Estado\s*\n([^\n]+)")
        municipio = extrair_campo_regex(texto, r"Município\s*\n([^\n]+)")
        entidade = extrair_campo_regex(texto, r"Entidade\s*\n([^\n]+)")
        cnpj = extrair_campo_regex(texto, r"CNPJ\s*\n([^\n]+)")
        tipo_proposta = extrair_campo_regex(texto, r"Tipo de Proposta\s*\n([^\n]+)")
        ano = extrair_campo_regex(texto, r"\bAno\s*\n([^\n]+)")
        valor_proposta = extrair_campo_regex(texto, r"Valor da Proposta\s*\n([^\n]+)")
        valor_total_empenho = extrair_campo_regex(texto, r"Valor Total de Empenho\s*\n([^\n]+)")
        valor_a_pagar = extrair_campo_regex(texto, r"Valor a Pagar\s*\n([^\n]+)")
        situacao_atual = extrair_campo_regex(texto, r"Situação Atual da Proposta\s*\n([^\n]+)")
        data_ultima_atualizacao = extrair_campo_regex(
            texto, r"Data da Última Atualização da Proposta\s*\n([^\n]+)"
        )

        # bloco do parlamentar
        bloco_parlamentar = extrair_bloco(
            texto,
            "Dados do Parlamentar",
            "Não foi constituído processo para essa proposta."
        )

        partido = None
        parlamentar = None
        numero_emenda = None
        valor_emenda = None

        if bloco_parlamentar:
            linhas = [l.strip() for l in bloco_parlamentar.splitlines() if l.strip()]
            linhas = [
                l for l in linhas
                if l not in ["Partido", "Nome Parlamentar", "Nº da Emenda", "Ano", "Valor da Emenda"]
            ]

            texto_unico = " ".join(linhas)

            m = re.search(
                r"\b([A-Z]{2,6})\s+(.+?)\s+(\d{6,10})\s+(20\d{2})\s+(R\$\s*[\d\.\,]+)",
                texto_unico
            )
            if m:
                partido = limpar(m.group(1))
                parlamentar = limpar(m.group(2))
                numero_emenda = limpar(m.group(3))
                valor_emenda = limpar(m.group(5))

        resultado = {
            "numero_proposta": numero,
            "estado": estado,
            "municipio": municipio,
            "entidade": entidade,
            "cnpj": cnpj,
            "tipo_proposta": tipo_proposta,
            "ano": ano,
            "valor_proposta": valor_proposta,
            "valor_total_empenho": valor_total_empenho,
            "valor_a_pagar": valor_a_pagar,
            "situacao_atual": situacao_atual,
            "data_ultima_atualizacao": data_ultima_atualizacao,
            "partido": partido,
            "parlamentar": parlamentar,
            "numero_emenda": numero_emenda,
            "valor_emenda": valor_emenda
        }

        return resultado

    except Exception as e:
        return {"erro": str(e)}

    finally:
        if driver:
            driver.quit()
