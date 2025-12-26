import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
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
    options = webdriver.ChromeOptions()
    # Modo headless é essencial para rodar em servidores como o Fly.io
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    prefs = {
        "download.default_directory": Config.TEMP_DIR,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


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
            # Tenta localizar o botão 'Pagar' para abrir os detalhes da fatura
            btn_pagar = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Pagar')]"))
            )
            driver.execute_script("arguments[0].click();", btn_pagar)

            # Localiza o botão de copiar código de barras
            btn_copiar = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Copiar Código de Barras')]"))
            )
            driver.execute_script("arguments[0].click();", btn_copiar)

            time.sleep(1)  # Pequena pausa para garantir que o clipboard seja atualizado
            codigo = pyperclip.paste()

            logger.info("💰 Código de barras LLZ copiado com sucesso!")
            return Boleto(
                origem="Finances/Condomínio (LLZ)",
                titulo="Fatura Condomínio - LLZ",
                linha_digitavel=codigo
            )

        except Exception:
            logger.info("🍃 Nenhuma fatura pendente encontrada na LLZ.")
            return None

    except Exception as e:
        logger.error(f"❌ Erro no scraper LLZ: {e}")
        return None
    finally:
        driver.quit()