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

    # Credenciais SEMAE/LLZ
    SEMAE_USER = os.getenv("SEMAE_USUARIO")
    SEMAE_CPF = os.getenv("SEMAE_CPF")
    SEMAE_PASS = os.getenv("SEMAE_SENHA")
    LLZ_USER = os.getenv("LLZ_USER")
    LLZ_PASS = os.getenv("LLZ_PASS")


# Garante que a pasta temporária existe
if not os.path.exists(Config.TEMP_DIR):
    os.makedirs(Config.TEMP_DIR)