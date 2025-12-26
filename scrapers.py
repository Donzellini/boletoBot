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
from python_anticaptcha import AnticaptchaClient

from utils import exibir_resultado


def configurar_driver():
    options = webdriver.ChromeOptions()
    # Configura download automático para a pasta temporária
    prefs = {
        "download.default_directory": "/tmp/boleto_bot",
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    # options.add_argument("--headless")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def scrap_semae_piracicaba():
    driver = configurar_driver()
    wait = WebDriverWait(driver, 20)

    # Chave extraída do seu HTML (k=...)
    SITE_KEY = "6Le9VR4bAAAAAPKYAoYNcXcq3JbLLKGdLI9hzwN4"

    try:
        driver.get("https://agenciaweb.semaepiracicaba.sp.gov.br/")

        print("⌨️ Preenchendo dados de acesso...")
        # Usuário (Matrícula)
        wait.until(EC.presence_of_element_located((By.ID, "NrMatriculaUnidade"))).send_keys(os.getenv("SEMAE_USUARIO"))

        # CPF
        driver.find_element(By.ID, "NrCpfCnpj").send_keys(os.getenv("SEMAE_CPF"))

        # Senha
        driver.find_element(By.ID, "sDsSenha").send_keys(os.getenv("SEMAE_SENHA"))

        print("🤖 Solicitando resolução do reCAPTCHA...")
        client = python_anticaptcha.AnticaptchaClient(os.getenv("ANTICAPTCHA_KEY"))
        task = python_anticaptcha.NoCaptchaTaskProxylessTask(driver.current_url, SITE_KEY)
        job = client.createTask(task)

        print("⏳ Aguardando worker do Anti-Captcha...")
        job.join()

        token = job.get_solution_response()

        # Injeção do Token no campo oculto do Google
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{token}";')

        print("🚀 Clicando em entrar...")
        # O botão 'ENTRAR' costuma ser um button ou input do tipo submit
        wait.until(EC.element_to_be_clickable((By.ID, "botao_login"))).click()

        print("✅ Login realizado com sucesso!")

        # 1. Clicar no elemento "MINHA AGÊNCIA" que leva para as faturas
        # Usamos o seletor CSS baseado no href que você mapeou
        print("📂 Tentando acessar 'Minha Agência'...")

        # XPath relativo: Procura um <a> que contenha o texto 'MINHA AGÊNCIA'
        xpath_agencia = "//a[contains(., 'MINHA AGÊNCIA')]"

        try:
            # 1. Espera o elemento estar visível
            elemento = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_agencia)))

            # 2. Tenta rolar até o elemento (scroll) para garantir que está na tela
            driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
            time.sleep(1)

            # 3. Tenta o clique via JavaScript (mais potente que o click() normal)
            driver.execute_script("arguments[0].click();", elemento)

            print("✅ Comando de clique enviado via JS!")

            # 4. Verifica se a URL mudou para confirmar o sucesso
            wait.until(EC.url_contains("SegundaVia"))
            print("🏁 Chegamos à tela de faturas!")

        except Exception as e:
            print(f"⚠️ Falha no clique: {e}")
            # Backup: Tenta o seu XPath específico se o relativo falhar
            print("🔄 Tentando via XPath absoluto de backup...")
            driver.find_element(By.XPATH, '//*[@id="app"]/div[3]/div/ul/li[1]/a').click()

    except Exception as e:
        print(f"❌ Erro crítico no scraper SEMAE: {e}")
    finally:
        print("🔌 Encerrando driver do SEMAE...")
        driver.quit()


def scrap_llz_condominio():
    driver = configurar_driver()
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://cliente.llzgarantidora.com.br/auth/entrar")

        # Login
        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(os.getenv("LLZ_USER"))
        driver.find_element(By.NAME, "password").send_keys(os.getenv("LLZ_PASS"))
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        print("🔓 Logado na LLZ! Buscando fatura em aberto...")

        # 1. Tenta encontrar o botão "Pagar"
        try:
            btn_pagar = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Pagar')]"))
            )

            # Força o clique via JavaScript para ignorar o Chat Widget
            driver.execute_script("arguments[0].click();", btn_pagar)
            print("💰 Botão 'Pagar' clicado via JS (contornando o chat)!")

            # 2. Clicar em "Copiar Código de Barras"
            # Também via JS para garantir, caso o chat mude de lugar
            btn_copiar = wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Copiar Código de Barras')]"))
            )
            driver.execute_script("arguments[0].click();", btn_copiar)
            print("📋 Botão 'Copiar Código de Barras' clicado via JS!")

            time.sleep(1)  # Garante que o sistema processou o clipboard
            codigo_capturado = pyperclip.paste()

            # Montamos o objeto no mesmo padrão do Gmail
            resultado_llz = {
                "label": "Finances/Condomínio (LLZ)",
                "assunto": "Boleto Condomínio - Dezembro",
                "pix": None,
                "linha_digitavel": codigo_capturado,
                "link_bevi": None
            }

            # Chamamos a função de exibição (que deve estar no main ou utilitários)
            exibir_resultado(resultado_llz)

        except Exception as e:
            print(f"⚠️ Nenhuma fatura com botão 'Pagar' encontrada na primeira linha: {e}")

    except Exception as e:
        print(f"❌ Erro no scraper LLZ: {e}")
    finally:
        # Deixe o quit comentado se quiser ver o código sendo copiado manualmente para testar
        # driver.quit()
        pass
