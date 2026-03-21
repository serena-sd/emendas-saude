import os, re, time, logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Emendas Saude", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

def get_chromedriver_path():
    for p in [
        os.environ.get("CHROMEDRIVER_PATH",""),
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/usr/lib/chromium/chromedriver",
        "/usr/lib/chromium-browser/chromedriver",
    ]:
        if p and os.path.isfile(p):
            logger.info(f"chromedriver: {p}"); return p
    return "chromedriver"

def get_chrome_bin():
    for p in [
        os.environ.get("CHROME_BIN",""),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ]:
        if p and os.path.isfile(p):
            logger.info(f"chrome: {p}"); return p
    return ""

def criar_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--mute-audio")
    opts.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
    chrome = get_chrome_bin()
    if chrome: opts.binary_location = chrome
    svc = Service(executable_path=get_chromedriver_path())
    return webdriver.Chrome(service=svc, options=opts)

def limpar(t):
    return " ".join((t or "").replace("\xa0"," ").split()).strip()

def regex(padrao, texto, g=1, flags=re.IGNORECASE):
    m = re.search(padrao, texto, flags)
    return limpar(m.group(g)) if m else ""

def parsear(body, html, numero):
    full = f"{body}\n{html}"
    r = {
        "numero_proposta":numero,"estado":"","municipio":"","entidade":"","cnpj":"",
        "tipo_proposta":"","ano":"","valor_proposta":"","valor_total_empenho":"",
        "valor_a_pagar":"","situacao_atual":"","data_ultima_atualizacao":"",
        "partido":"","parlamentar":"","numero_emenda":"","valor_emenda":""
    }
    # 1. JSON embutido
    for campo, chave in [("estado","estado"),("municipio","municipio"),("entidade","entidade"),
        ("cnpj","cnpj"),("tipo_proposta","tipo_proposta"),("ano","ano"),
        ("valor_proposta","valor_proposta"),("valor_total_empenho","valor_total_empenho"),
        ("valor_a_pagar","valor_a_pagar"),("situacao_atual","situacao_atual"),
        ("data_ultima_atualizacao","data_ultima_atualizacao")]:
        v = regex(rf'"{chave}"\s*:\s*"([^"]*)"', html)
        if v: r[campo] = v
    # 2. Fallback texto visivel
    if not r["estado"]: r["estado"] = regex(r"Estado[:\-]?\s*([A-Z]{2})\b", body)
    if not r["municipio"]: r["municipio"] = regex(r"Munic[íi]pio[:\-]?\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀ-Ú\s]+?)(?:\n|Estado|CNPJ|$)", body)
    if not r["entidade"]: r["entidade"] = regex(r"Entidade[:\-]?\s*(.+?)(?:\n|CNPJ|$)", body)
    if not r["cnpj"]:
        m = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", full)
        r["cnpj"] = m.group(0) if m else ""
    if not r["tipo_proposta"]: r["tipo_proposta"] = regex(r"Tipo da Proposta[:\-]?\s*(.+?)(?:\n|Ano|Valor|$)", body)
    if not r["ano"]: r["ano"] = regex(r"\bAno[:\-]?\s*(20\d{2})\b", body)
    if not r["valor_proposta"]: r["valor_proposta"] = regex(r"Valor da Proposta[:\-]?\s*(R\$\s*[\d\.,]+)", body)
    if not r["valor_total_empenho"]: r["valor_total_empenho"] = regex(r"Valor Total Empenho[:\-]?\s*(R\$\s*[\d\.,]+)", body)
    if not r["valor_a_pagar"]: r["valor_a_pagar"] = regex(r"Valor a Pagar[:\-]?\s*(R\$\s*[\d\.,]+)", body)
    if not r["situacao_atual"]: r["situacao_atual"] = regex(r"Situa[çc][aã]o Atual[:\-]?\s*(.+?)(?:\n|Data|$)", body)
    if not r["data_ultima_atualizacao"]: r["data_ultima_atualizacao"] = regex(r"Data da[:\-]?\s*[Úú]ltima Atualiza[çc][aã]o[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})", body)
    # 3. Bloco emenda (parlamentar/partido)
    trecho = regex(r"Partido\s+Parlamentar.+?Valor da Emenda\s+(.+?)(?:N[aã]o foi constitu|Voltar|$)", body)
    if not trecho:
        m2 = re.search(r"\b[A-Z]{2,5}\s+.+?\s+\d{6,10}\s+\d{4}\s+R\$\s*[\d\.,]+", body)
        trecho = m2.group(0) if m2 else ""
    if trecho:
        m3 = re.search(r"\b([A-Z]{2,5})\s+(.+?)\s+(\d{6,10})\s+\d{4}\s+(R\$\s*[\d\.,]+)", trecho)
        if m3:
            r["partido"] = limpar(m3.group(1))
            r["parlamentar"] = limpar(m3.group(2))
            r["numero_emenda"] = limpar(m3.group(3))
            r["valor_emenda"] = limpar(m3.group(4))
    return r

@app.get("/")
def home():
    return {"status":"online","versao":"2.0","chromedriver":get_chromedriver_path(),"chrome":get_chrome_bin()}

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/proposta/{numero}")
def consultar_proposta(numero: str):
    driver = None
    try:
        logger.info(f"Buscando proposta: {numero}")
        driver = criar_driver()
        url = f"https://infoms.saude.gov.br/extensions/TransferenciaFundoaFundo/TransferenciaFundoaFundo.html#/proposta/{numero}"
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(10)  # aguarda Angular/Vue renderizar
        body = driver.find_element(By.TAG_NAME, "body").text
        html = driver.page_source
        logger.info(f"Body: {len(body)} chars")
        resultado = parsear(body, html, numero)
        logger.info(f"municipio={resultado['municipio']} tipo={resultado['tipo_proposta']}")
        return resultado
    except Exception as e:
        logger.error(f"Erro: {e}")
        return {"numero_proposta":numero,"estado":"","municipio":"","entidade":"","cnpj":"",
                "tipo_proposta":"","ano":"","valor_proposta":"","valor_total_empenho":"",
                "valor_a_pagar":"","situacao_atual":"","data_ultima_atualizacao":"",
                "partido":"","parlamentar":"","numero_emenda":"","valor_emenda":"","erro":str(e)}
    finally:
        if driver:
            try: driver.quit()
            except: pass
