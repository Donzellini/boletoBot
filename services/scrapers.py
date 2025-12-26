import os
import time
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import python_anticaptcha

# Imports da nova estrutura
from core.models import Boleto

from core.config import Config
from utils.helpers import logger


def configurar_driver():
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": Config.TEMP_DIR,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def scrap_semae_piracicaba():
    driver = configurar_driver()
    wait = WebDriverWait(driver, 20)
    SITE_KEY = "6Le9VR4bAAAAAPKYAoYNcXcq3JbLLKGdLI9hzwN4"

    try:
        driver.get("https://agenciaweb.semaepiracicaba.sp.gov.br/")
        logger.info("⌨️ Preenchendo SEMAE...")
        wait.until(EC.presence_of_element_located((By.ID, "NrMatriculaUnidade"))).send_keys(Config.SEMAE_USER)
        driver.find_element(By.ID, "NrCpfCnpj").send_keys(Config.SEMAE_CPF)
        driver.find_element(By.ID, "sDsSenha").send_keys(Config.SEMAE_PASS)

        # Captcha
        client = python_anticaptcha.AnticaptchaClient(Config.ANTICAPTCHA_KEY)
        task = python_anticaptcha.NoCaptchaTaskProxylessTask(driver.current_url, SITE_KEY)
        job = client.createTask(task)
        logger.info("⏳ Resolvendo Captcha SEMAE...")
        job.join()

        token = job.get_solution_response()
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{token}";')
        driver.find_element(By.ID, "botao_login").click()

        logger.info("✅ Login SEMAE realizado!")
        # Lógica de navegação para Segunda Via aqui...

    except Exception as e:
        logger.error(f"❌ Erro SEMAE: {e}")
    finally:
        driver.quit()


def scrap_llz_condominio():
    driver = configurar_driver()
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://cliente.llzgarantidora.com.br/auth/entrar")

        logger.info("🔑 Realizando login no portal LLZ...")
        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(Config.LLZ_USER)
        driver.find_element(By.NAME, "password").send_keys(Config.LLZ_PASS)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 1. Busca botão Pagar
        try:
            logger.info("💰 Fatura aberta encontrada! Copiando código...")

            btn_pagar = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Pagar')]"))
            )
            driver.execute_script("arguments[0].click();", btn_pagar)

            # 2. Copiar Código
            btn_copiar = wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Copiar Código de Barras')]"))
            )
            driver.execute_script("arguments[0].click();", btn_copiar)

            time.sleep(1)
            codigo = pyperclip.paste()

            # Retorna o Objeto Boleto (em vez de dicionário) para evitar o erro
            return Boleto(
                origem="Finances/Condomínio (LLZ)",
                titulo="Fatura Condomínio - LLZ",
                linha_digitavel=codigo
            )

        except Exception:
            logger.warning("🍃 Nenhuma fatura pendente na LLZ no momento.")
            return None

    except Exception as e:
        logger.error(f"❌ Erro LLZ: {e}")
        return None
    finally:
        driver.quit()