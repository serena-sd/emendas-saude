import os, re, time, logging, threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Emendas FNS", version="5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# ── Keep-alive: pinga a si mesmo a cada 14min para nunca dormir ──
def keep_alive():
    import urllib.request
    while True:
        time.sleep(14 * 60)
        try:
            urllib.request.urlopen("https://emendas-saude.onrender.com/health", timeout=10)
            logger.info("keep-alive ping ok")
        except Exception as e:
            logger.warning(f"keep-alive falhou: {e}")

threading.Thread(target=keep_alive, daemon=True).start()

# ── Helpers ──────────────────────────────────────────────────────
def limpar(t):
    return " ".join((t or "").replace("\xa0", " ").split()).strip()

def regex(padrao, texto, g=1):
    m = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
    return limpar(m.group(g)) if m else ""

def parsear(body, html, numero):
    r = {k: "" for k in [
        "numero_proposta","municipio","estado","entidade","cnpj",
        "tipo_proposta","ano","valor_proposta","valor_total_empenho",
        "valor_a_pagar","situacao_atual","data_ultima_atualizacao",
        "partido","parlamentar","numero_emenda","valor_emenda"
    ]}
    r["numero_proposta"] = numero

    # 1. JSON embutido no HTML
    for campo, chave in [
        ("municipio","municipio"), ("estado","estado"),
        ("entidade","entidade"),   ("cnpj","cnpj"),
        ("tipo_proposta","tipoProposta"), ("ano","ano"),
        ("valor_proposta","valorProposta"),
        ("situacao_atual","situacaoAtual"),
        ("data_ultima_atualizacao","dataUltimaAtualizacao"),
    ]:
        v = regex(rf'"{chave}"\s*:\s*"([^"]+)"', html)
        if v: r[campo] = v

    # 2. Texto visível da página
    if not r["municipio"]:
        r["municipio"] = regex(
            r"Munic[íi]pio\s*:?\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀ-Ú\s]+?)(?:\n|Estado|CNPJ|$)", body)
    if not r["estado"]:
        r["estado"] = regex(r"Estado\s*:?\s*([A-Z]{2})\b", body)
    if not r["entidade"]:
        r["entidade"] = regex(r"Entidade\s*:?\s*(.+?)(?:\n|CNPJ|$)", body)
    if not r["cnpj"]:
        m = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", body + html)
        r["cnpj"] = m.group(0) if m else ""
    if not r["tipo_proposta"]:
        r["tipo_proposta"] = regex(
            r"Tipo da Proposta\s*:?\s*(.+?)(?:\n|Ano|Valor|$)", body)
    if not r["ano"]:
        r["ano"] = regex(r"\bAno\s*:?\s*(20\d{2})\b", body)
    if not r["valor_proposta"]:
        r["valor_proposta"] = regex(
            r"Valor da Proposta\s*:?\s*(R\$\s*[\d\.,]+)", body)
    if not r["valor_total_empenho"]:
        r["valor_total_empenho"] = regex(
            r"Valor Total Empenho\s*:?\s*(R\$\s*[\d\.,]+)", body)
    if not r["valor_a_pagar"]:
        r["valor_a_pagar"] = regex(
            r"Valor a Pagar\s*:?\s*(R\$\s*[\d\.,]+)", body)
    if not r["situacao_atual"]:
        r["situacao_atual"] = regex(
            r"Situa[çc][aã]o Atual\s*:?\s*(.+?)(?:\n|Data|$)", body)
    if not r["data_ultima_atualizacao"]:
        r["data_ultima_atualizacao"] = regex(
            r"[Úú]ltima Atualiza[çc][aã]o\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", body)

    # 3. Bloco da emenda: PL ZUCCO 44840001 2026 R$ 400.000,00
    m_emenda = re.search(
        r"\b([A-Z]{2,5})\s+([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀ-Ú\s]+?)\s+(\d{6,10})\s+(20\d{2})\s+(R\$\s*[\d\.,]+)",
        body)
    if m_emenda:
        r["partido"]       = limpar(m_emenda.group(1))
        r["parlamentar"]   = limpar(m_emenda.group(2))
        r["numero_emenda"] = limpar(m_emenda.group(3))
        r["ano"]           = r["ano"] or limpar(m_emenda.group(4))
        r["valor_emenda"]  = limpar(m_emenda.group(5))

    return r

# ── Selenium driver ───────────────────────────────────────────────
def criar_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    opts = Options()
    for arg in ["--headless=new","--no-sandbox","--disable-dev-shm-usage",
                "--disable-gpu","--window-size=1920,1080",
                "--disable-extensions","--disable-background-networking","--mute-audio"]:
        opts.add_argument(arg)

    for chrome in ["/usr/bin/google-chrome","/usr/bin/chromium","/usr/bin/chromium-browser"]:
        if os.path.isfile(chrome):
            opts.binary_location = chrome
            break

    driver_path = "chromedriver"
    for drv in ["/usr/bin/chromedriver","/usr/local/bin/chromedriver",
                "/usr/lib/chromium/chromedriver"]:
        if os.path.isfile(drv):
            driver_path = drv
            break

    return webdriver.Chrome(service=Service(executable_path=driver_path), options=opts)

# ── Endpoints ─────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"status": "online", "versao": "5.0", "keep_alive": "ativo"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/proposta/{numero}")
def consultar(numero: str):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = None
    try:
        logger.info(f"Buscando proposta: {numero}")
        driver = criar_driver()

        url = (f"https://infoms.saude.gov.br/extensions/TransferenciaFundoaFundo/"
               f"TransferenciaFundoaFundo.html#/proposta/{numero}")
        driver.get(url)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(10)

        body = driver.find_element(By.TAG_NAME, "body").text
        html = driver.page_source
        logger.info(f"Body: {len(body)} chars")

        resultado = parsear(body, html, numero)
        logger.info(f"municipio={resultado['municipio']} tipo={resultado['tipo_proposta']}")
        return resultado

    except Exception as e:
        logger.error(f"Erro: {e}")
        return {
            "numero_proposta": numero,
            "municipio":"","estado":"","entidade":"","cnpj":"",
            "tipo_proposta":"","ano":"","valor_proposta":"",
            "valor_total_empenho":"","valor_a_pagar":"",
            "situacao_atual":"","data_ultima_atualizacao":"",
            "partido":"","parlamentar":"","numero_emenda":"","valor_emenda":"",
            "erro": str(e)
        }
    finally:
        if driver:
            try: driver.quit()
            except: pass
