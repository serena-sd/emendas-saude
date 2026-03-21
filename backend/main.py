from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois podemos restringir para o GitHub Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def criar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def texto_limpo(texto: str) -> str:
    if not texto:
        return ""
    return " ".join(texto.replace("\xa0", " ").split()).strip()


def extrair_valor_monetario(texto: str) -> str:
    if not texto:
        return ""
    m = re.search(r"R\$\s*[\d\.\,]+", texto)
    return m.group(0).strip() if m else ""


def extrair_cnpj(texto: str) -> str:
    if not texto:
        return ""
    m = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", texto)
    return m.group(0) if m else ""


def extrair_emenda_de_texto(texto: str):
    """
    Exemplo esperado no texto:
    PL ZUCCO 44840001 2026 R$ 400.000,00
    """
    texto = texto_limpo(texto)

    resultado = {
        "partido": "",
        "parlamentar": "",
        "numero_emenda": "",
        "valor_emenda": ""
    }

    if not texto:
        return resultado

    match = re.search(
        r"\b([A-Z]{2,5})\s+(.+?)\s+(\d{6,10})\s+(\d{4})\s+(R\$\s*[\d\.\,]+)",
        texto
    )

    if match:
        resultado["partido"] = texto_limpo(match.group(1))
        resultado["parlamentar"] = texto_limpo(match.group(2))
        resultado["numero_emenda"] = texto_limpo(match.group(3))
        resultado["valor_emenda"] = texto_limpo(match.group(5))

    return resultado


def extrair_campo_por_rotulo(texto: str, rotulo: str) -> str:
    """
    Procura algo como:
    Município: CIDREIRA
    Estado: RS
    ...
    """
    padrao = rf"{re.escape(rotulo)}\s*[:\-]?\s*(.+)"
    m = re.search(padrao, texto, re.IGNORECASE)
    if m:
        valor = m.group(1).split("\n")[0].strip()
        return texto_limpo(valor)
    return ""


def parsear_texto_pagina(texto: str, numero_proposta: str):
    texto = texto_limpo(texto)

    resultado = {
        "numero_proposta": numero_proposta,
        "estado": "",
        "municipio": "",
        "entidade": "",
        "cnpj": "",
        "tipo_proposta": "",
        "ano": "",
        "valor_proposta": "",
        "valor_total_empenho": "",
        "valor_a_pagar": "",
        "situacao_atual": "",
        "data_ultima_atualizacao": "",
        "partido": "",
        "parlamentar": "",
        "numero_emenda": "",
        "valor_emenda": ""
    }

    # Campos básicos por regex/rotulo
    m_estado = re.search(r'"estado":"([^"]+)"', texto)
    if m_estado:
        resultado["estado"] = m_estado.group(1)

    m_municipio = re.search(r'"municipio":"([^"]+)"', texto)
    if m_municipio:
        resultado["municipio"] = m_municipio.group(1)

    m_entidade = re.search(r'"entidade":"([^"]+)"', texto)
    if m_entidade:
        resultado["entidade"] = m_entidade.group(1)

    m_cnpj = re.search(r'"cnpj":"([^"]+)"', texto)
    if m_cnpj:
        resultado["cnpj"] = m_cnpj.group(1)

    m_tipo = re.search(r'"tipo_proposta":"([^"]+)"', texto)
    if m_tipo:
        resultado["tipo_proposta"] = m_tipo.group(1)

    m_ano = re.search(r'"ano":"([^"]+)"', texto)
    if m_ano:
        resultado["ano"] = m_ano.group(1)

    m_valor_proposta = re.search(r'"valor_proposta":"([^"]+)"', texto)
    if m_valor_proposta:
        resultado["valor_proposta"] = m_valor_proposta.group(1)

    m_total_empenho = re.search(r'"valor_total_empenho":"([^"]+)"', texto)
    if m_total_empenho:
        resultado["valor_total_empenho"] = m_total_empenho.group(1)

    m_a_pagar = re.search(r'"valor_a_pagar":"([^"]+)"', texto)
    if m_a_pagar:
        resultado["valor_a_pagar"] = m_a_pagar.group(1)

    m_situacao = re.search(r'"situacao_atual":"([^"]+)"', texto)
    if m_situacao:
        resultado["situacao_atual"] = m_situacao.group(1)

    m_data = re.search(r'"data_ultima_atualizacao":"([^"]*)"', texto)
    if m_data:
        resultado["data_ultima_atualizacao"] = m_data.group(1)

    # fallback se algum campo não vier nesse bloco
    if not resultado["estado"]:
        m = re.search(r"\bEstado[:\-]?\s*([A-Z]{2})\b", texto, re.IGNORECASE)
        if m:
            resultado["estado"] = texto_limpo(m.group(1))

    if not resultado["municipio"]:
        m = re.search(r"\bMunicípio[:\-]?\s*([A-ZÀ-Ú\s]+)", texto, re.IGNORECASE)
        if m:
            resultado["municipio"] = texto_limpo(m.group(1))

    if not resultado["entidade"]:
        m = re.search(r"\bEntidade[:\-]?\s*(.+?)(?:\bCNPJ\b|$)", texto, re.IGNORECASE)
        if m:
            resultado["entidade"] = texto_limpo(m.group(1))

    if not resultado["cnpj"]:
        resultado["cnpj"] = extrair_cnpj(texto)

    if not resultado["tipo_proposta"]:
        m = re.search(r"\bTipo da Proposta[:\-]?\s*(.+?)(?:\bAno\b|\bValor\b|$)", texto, re.IGNORECASE)
        if m:
            resultado["tipo_proposta"] = texto_limpo(m.group(1))

    if not resultado["ano"]:
        m = re.search(r"\bAno[:\-]?\s*(20\d{2})\b", texto, re.IGNORECASE)
        if m:
            resultado["ano"] = texto_limpo(m.group(1))

    if not resultado["valor_proposta"]:
        m = re.search(r"\bValor da Proposta[:\-]?\s*(R\$\s*[\d\.\,]+)", texto, re.IGNORECASE)
        if m:
            resultado["valor_proposta"] = texto_limpo(m.group(1))

    if not resultado["valor_total_empenho"]:
        m = re.search(r"\bValor Total Empenho[:\-]?\s*(R\$\s*[\d\.\,]+)", texto, re.IGNORECASE)
        if m:
            resultado["valor_total_empenho"] = texto_limpo(m.group(1))

    if not resultado["valor_a_pagar"]:
        m = re.search(r"\bValor a Pagar[:\-]?\s*(R\$\s*[\d\.\,]+)", texto, re.IGNORECASE)
        if m:
            resultado["valor_a_pagar"] = texto_limpo(m.group(1))

    if not resultado["situacao_atual"]:
        m = re.search(r"\bSituação Atual[:\-]?\s*(.+?)(?:\bData da Última Atualização\b|$)", texto, re.IGNORECASE)
        if m:
            resultado["situacao_atual"] = texto_limpo(m.group(1))

    if not resultado["data_ultima_atualizacao"]:
        m = re.search(r"\bData da Última Atualização[:\-]?\s*([0-3]?\d/[0-1]?\d/\d{4})", texto, re.IGNORECASE)
        if m:
            resultado["data_ultima_atualizacao"] = texto_limpo(m.group(1))

    # trecho da emenda
    trecho_emenda = ""
    m_emenda_bloco = re.search(
        r"(?:Partido\s+Parlamentar\s+Nº da Emenda.*?Valor da Emenda\s+)(.+?)(?:\bNão foi constituído processo\b|\bVoltar\b|$)",
        texto,
        re.IGNORECASE
    )
    if m_emenda_bloco:
        trecho_emenda = texto_limpo(m_emenda_bloco.group(1))
    else:
        # fallback: procura linha com padrão conhecido
        m_linha = re.search(r"\b[A-Z]{2,5}\s+.+?\s+\d{6,10}\s+\d{4}\s+R\$\s*[\d\.\,]+", texto)
        if m_linha:
            trecho_emenda = texto_limpo(m_linha.group(0))

    dados_emenda = extrair_emenda_de_texto(trecho_emenda)
    resultado["partido"] = dados_emenda["partido"]
    resultado["parlamentar"] = dados_emenda["parlamentar"]
    resultado["numero_emenda"] = dados_emenda["numero_emenda"]
    resultado["valor_emenda"] = dados_emenda["valor_emenda"]

    return resultado


@app.get("/")
def home():
    return {"status": "API profissional rodando"}


@app.get("/proposta/{numero}")
def consultar_proposta(numero: str):
    driver = None
    try:
        driver = criar_driver()
        url = f"https://infoms.saude.gov.br/extensions/TransferenciaFundoaFundo/TransferenciaFundoaFundo.html#/proposta/{numero}"
        driver.get(url)

        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        time.sleep(8)

        texto_pagina = driver.find_element(By.TAG_NAME, "body").text
        html_pagina = driver.page_source

        # Junta body + source porque às vezes um campo aparece em um e não no outro
        texto_total = f"{texto_pagina}\n{html_pagina}"

        resultado = parsear_texto_pagina(texto_total, numero)
        return resultado

    except Exception as e:
        return {
            "numero_proposta": numero,
            "estado": "",
            "municipio": "",
            "entidade": "",
            "cnpj": "",
            "tipo_proposta": "",
            "ano": "",
            "valor_proposta": "",
            "valor_total_empenho": "",
            "valor_a_pagar": "",
            "situacao_atual": "",
            "data_ultima_atualizacao": "",
            "partido": "",
            "parlamentar": "",
            "numero_emenda": "",
            "valor_emenda": "",
            "erro": str(e)
        }
    finally:
        if driver:
            driver.quit()
