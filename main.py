import os, re, time, logging, threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Emendas FNS", version="7.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

def _keep_alive():
    import urllib.request
    url = os.environ.get("RENDER_EXTERNAL_URL","https://emendas-saude.onrender.com")
    while True:
        time.sleep(14*60)
        try:
            urllib.request.urlopen(f"{url}/health", timeout=10)
            logger.info("keep-alive ok")
        except Exception as e:
            logger.warning(f"keep-alive: {e}")

threading.Thread(target=_keep_alive, daemon=True).start()

def limpar(t):
    return " ".join((t or "").replace("\xa0"," ").split()).strip()

def criar_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    for a in ["--headless=new","--no-sandbox","--disable-dev-shm-usage",
              "--disable-gpu","--window-size=1920,1080","--disable-extensions",
              "--mute-audio","--disable-background-networking"]:
        opts.add_argument(a)

    for chrome in ["/usr/bin/google-chrome","/usr/bin/google-chrome-stable",
                   "/usr/bin/chromium","/usr/bin/chromium-browser"]:
        if os.path.isfile(chrome):
            opts.binary_location = chrome
            logger.info(f"Chrome: {chrome}")
            break

    for drv in ["/usr/bin/chromedriver","/usr/local/bin/chromedriver"]:
        if os.path.isfile(drv):
            return webdriver.Chrome(service=Service(drv), options=opts)

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts)

# ── Endpoints ────────────────────────────────────────────────────
@app.get("/")
def home(): return {"status":"online","versao":"7.0"}

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/debug/pagina")
def debug_pagina():
    """Vê a estrutura da página de emendas para entender os campos"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    driver = None
    try:
        driver = criar_driver()
        url = "https://investsuspaineis.saude.gov.br/extensions/CGIN_Painel_Emendas/CGIN_Painel_Emendas.html"
        logger.info(f"Abrindo: {url}")
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(8)

        body = driver.find_element(By.TAG_NAME, "body").text
        url_atual = driver.current_url
        titulo = driver.title

        # Captura todos os selects/inputs da página
        selects = []
        for s in driver.find_elements(By.TAG_NAME, "select"):
            try:
                selects.append({
                    "id": s.get_attribute("id"),
                    "name": s.get_attribute("name"),
                    "class": s.get_attribute("class"),
                    "options_count": len(s.find_elements(By.TAG_NAME, "option")),
                    "options_text": [o.text for o in s.find_elements(By.TAG_NAME, "option")][:5]
                })
            except: pass

        inputs = []
        for i in driver.find_elements(By.TAG_NAME, "input"):
            try:
                inputs.append({
                    "id": i.get_attribute("id"),
                    "name": i.get_attribute("name"),
                    "placeholder": i.get_attribute("placeholder"),
                    "type": i.get_attribute("type"),
                })
            except: pass

        buttons = []
        for b in driver.find_elements(By.TAG_NAME, "button"):
            try:
                buttons.append({"text": b.text, "id": b.get_attribute("id")})
            except: pass

        return {
            "url_acessada": url_atual,
            "titulo": titulo,
            "body_preview": body[:2000],
            "selects": selects,
            "inputs": inputs,
            "buttons": buttons,
        }
    except Exception as e:
        logger.error(f"Erro debug: {e}")
        return {"erro": str(e)}
    finally:
        if driver:
            try: driver.quit()
            except: pass

@app.get("/emendas/municipio/{municipio}/ano/{ano}")
def buscar_por_municipio(municipio: str, ano: str = "2026"):
    """Busca todas as emendas de um município em um ano"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.select import Select

    driver = None
    try:
        logger.info(f"Buscando emendas: {municipio} / {ano}")
        driver = criar_driver()
        url = "https://investsuspaineis.saude.gov.br/extensions/CGIN_Painel_Emendas/CGIN_Painel_Emendas.html"
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(8)

        # Tenta selecionar o ano
        try:
            sel_ano = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                    "//select[.//option[contains(text(),'2026')]]")))
            Select(sel_ano).select_by_visible_text(ano)
            time.sleep(2)
            logger.info(f"Ano {ano} selecionado")
        except Exception as e:
            logger.warning(f"Não selecionou ano: {e}")

        # Tenta preencher o município (input de texto ou select)
        try:
            # Tenta input de texto primeiro
            inp_mun = driver.find_element(By.XPATH,
                "//input[@placeholder[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'munic')]]")
            inp_mun.clear()
            inp_mun.send_keys(municipio)
            time.sleep(2)
            logger.info(f"Município digitado: {municipio}")
        except:
            try:
                # Tenta select de município
                sel_mun = driver.find_element(By.XPATH,
                    "//select[.//option[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'munic') or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cidreira') or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'selecione')]]")
                for opt in sel_mun.find_elements(By.TAG_NAME, "option"):
                    if municipio.upper() in opt.text.upper():
                        opt.click()
                        break
                time.sleep(2)
                logger.info(f"Município selecionado no select")
            except Exception as e:
                logger.warning(f"Não selecionou município: {e}")

        # Clica no botão de pesquisa/consulta
        try:
            btn = driver.find_element(By.XPATH,
                "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'consultar') or contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'pesquisar') or contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'buscar')]")
            btn.click()
            time.sleep(5)
            logger.info("Botão clicado")
        except Exception as e:
            logger.warning(f"Botão não encontrado: {e}")

        body = driver.find_element(By.TAG_NAME, "body").text
        html = driver.page_source
        logger.info(f"Body resultado: {len(body)} chars")
        logger.info(f"Preview: {body[:500]}")

        return {
            "municipio": municipio,
            "ano": ano,
            "url": driver.current_url,
            "body_preview": body[:3000],
            "total_chars": len(body),
        }

    except Exception as e:
        logger.error(f"Erro: {e}")
        return {"erro": str(e)}
    finally:
        if driver:
            try: driver.quit()
            except: pass

@app.get("/proposta/{numero}")
def consultar(numero: str):
    """Mantido para compatibilidade — redireciona para busca por município"""
    return {
        "numero_proposta": numero,
        "municipio":"","estado":"","entidade":"","cnpj":"",
        "tipo_proposta":"","ano":"","valor_proposta":"",
        "valor_total_empenho":"","valor_a_pagar":"",
        "situacao_atual":"","data_ultima_atualizacao":"",
        "partido":"","parlamentar":"","numero_emenda":"","valor_emenda":"",
        "info": "Use /debug/pagina primeiro para entender a estrutura, depois /emendas/municipio/CIDREIRA/ano/2026"
    }
