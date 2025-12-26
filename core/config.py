import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GMAIL_USER = os.getenv('GMAIL_USER')
    GMAIL_PASS = os.getenv('GMAIL_APP_PASSWORD')
    raw_labels = os.getenv("LABELS_INTERESSE", "")
    LABELS_INTERESSE = [l.strip() for l in raw_labels.split(",") if l.strip()]

    CPF_SENHA = os.getenv("CPF_SENHA")
    ANTICAPTCHA_KEY = os.getenv("ANTICAPTCHA_KEY")
    TEMP_DIR = '/tmp/boleto_bot'

    # Credenciais
    SEMAE_USER = os.getenv("SEMAE_USUARIO")
    SEMAE_CPF = os.getenv("SEMAE_CPF")
    SEMAE_PASS = os.getenv("SEMAE_SENHA")
    LLZ_USER = os.getenv("LLZ_USER")
    LLZ_PASS = os.getenv("LLZ_PASS")

    # Lista bruta de nomes de funções vindas da env
    raw_scrapers = os.getenv("SCRAPERS_ATIVOS", "")
    LISTA_FUNCOES_SCRAPERS = [s.strip() for s in raw_scrapers.split(",") if s.strip()]

    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


if not os.path.exists(Config.TEMP_DIR):
    os.makedirs(Config.TEMP_DIR)