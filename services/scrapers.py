import re
import time
import os
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import python_anticaptcha
import pyperclip

# Imports internos
from core.models import Boleto
from core.config import Config
from core.logger import logger


def configurar_driver():
    """Configura o WebDriver para rodar em modo headless e gerenciar downloads."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--proxy-server='direct://'")
    options.add_argument("--proxy-bypass-list=*")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--single-process")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-background-timer-throttling")
    prefs = {
        "download.default_directory": Config.TEMP_DIR,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)

    if os.path.exists("/data"):
        options.binary_location = "/usr/bin/chromium"
        service = Service(executable_path="/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())

    return webdriver.Chrome(service=service, options=options)


def scrap_semae_piracicaba():
    """Scraper para o portal do SEMAE Piracicaba com resolução de Captcha."""
    driver = configurar_driver()
    wait = WebDriverWait(driver, 20)
    SITE_KEY = "6Le9VR4bAAAAAPKYAoYNcXcq3JbLLKGdLI9hzwN4"

    try:
        driver.get("https://agenciaweb.semaepiracicaba.sp.gov.br/")
        logger.info("⌨️ Preenchendo dados SEMAE...")

        wait.until(EC.presence_of_element_located((By.ID, "NrMatriculaUnidade"))).send_keys(Config.SEMAE_USER)
        driver.find_element(By.ID, "NrCpfCnpj").send_keys(Config.SEMAE_CPF)
        driver.find_element(By.ID, "sDsSenha").send_keys(Config.SEMAE_PASS)

        # Resolução de Captcha via Anti-Captcha
        client = python_anticaptcha.AnticaptchaClient(Config.ANTICAPTCHA_KEY)
        task = python_anticaptcha.NoCaptchaTaskProxylessTask(driver.current_url, SITE_KEY)
        job = client.createTask(task)
        logger.info("⏳ Resolvendo Captcha SEMAE...")
        job.join()

        token = job.get_solution_response()
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{token}";')
        driver.find_element(By.ID, "botao_login").click()

        logger.info("✅ Login SEMAE realizado com sucesso!")
        # TODO: Adicionar lógica de navegação para extração da linha digitável se necessário
        return None

    except Exception as e:
        logger.error(f"❌ Erro no scraper SEMAE: {e}")
        return None
    finally:
        driver.quit()


def scrap_llz_condominio():
    """Scraper para o portal LLZ Garantidora para copiar código de barras do condomínio."""
    driver = configurar_driver()
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://cliente.llzgarantidora.com.br/auth/entrar")
        logger.info("🔑 Realizando login no portal LLZ...")

        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(Config.LLZ_USER)
        driver.find_element(By.NAME, "password").send_keys(Config.LLZ_PASS)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        try:

            try:
                elemento_valor = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'R$')]"))
                )
                valor_texto = elemento_valor.text.replace('R$', '').replace('\xa0', '').strip()
                logger.info(f"💰 Valor LLZ identificado: R$ {valor_texto}")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível capturar o valor da LLZ: {e}")
                valor_texto = None

            try:
                elementos = driver.find_elements(By.XPATH, "//*[contains(text(), '/20')]")

                data_vencimento = None
                for el in elementos:
                    match = re.search(r'(\d{2}/\d{2}/\d{4})', el.text)
                    if match:
                        data_vencimento = match.group(1)
                        break

                if data_vencimento:
                    mes_ref = "/".join(data_vencimento.split("/")[1:])
                    logger.info(f"📅 Mês de referência LLZ: {mes_ref}")
                else:
                    mes_ref = datetime.now().strftime("%m/%Y")

            except Exception as e:
                logger.warning(f"⚠️ Erro ao extrair data, usando mês atual: {e}")
                mes_ref = datetime.now().strftime("%m/%Y")

            btn_pagar = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Pagar')]"))
            )
            driver.execute_script("arguments[0].click();", btn_pagar)

            driver.execute_script("""
                window.ultimo_codigo_copiado = "";
                navigator.clipboard.writeText = function(text) {
                    window.ultimo_codigo_copiado = text;
                    return Promise.resolve();
                };
            """)

            btn_copiar = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Copiar Código de Barras')]"))
            )
            driver.execute_script("arguments[0].click();", btn_copiar)

            time.sleep(2)
            codigo = driver.execute_script("return window.ultimo_codigo_copiado;")

            logger.info("💰 Código de barras LLZ copiado com sucesso!")
            return Boleto(
                origem="Finances/Condomínio (LLZ)",
                titulo="Fatura Condomínio - LLZ",
                valor=valor_texto,
                linha_digitavel=codigo,
                mes_referencia = mes_ref
            )

        except Exception as e:
            logger.info(f"🍃 Nenhuma fatura pendente encontrada na LLZ. Erro: {e}")
            return None

    except Exception as e:
        logger.error(f"❌ Erro no scraper LLZ: {e}")
        return None
    finally:
        driver.quit()


if __name__ == '__main__':
    boleto_llz = scrap_llz_condominio()
    logger.info(boleto_llz)
