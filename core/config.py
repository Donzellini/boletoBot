import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()


class Config:
    # --- GMAIL ---
    GMAIL_USER = os.getenv('GMAIL_USER')
    GMAIL_PASS = os.getenv('GMAIL_APP_PASSWORD')
    raw_labels = os.getenv("LABELS_INTERESSE", "")
    LABELS_INTERESSE = [l.strip() for l in raw_labels.split(",") if l.strip()]

    # --- SEGURANÇA E DIRETÓRIOS ---
    CPF_SENHA = os.getenv("CPF_SENHA")
    ANTICAPTCHA_KEY = os.getenv("ANTICAPTCHA_KEY")
    TEMP_DIR = '/tmp/boleto_bot'

    # --- CREDENCIAIS DE PORTAIS (SCRAPERS) ---
    SEMAE_USER = os.getenv("SEMAE_USUARIO")
    SEMAE_CPF = os.getenv("SEMAE_CPF")
    SEMAE_PASS = os.getenv("SEMAE_SENHA")
    LLZ_USER = os.getenv("LLZ_USER")
    LLZ_PASS = os.getenv("LLZ_PASS")

    # Lista de funções de scrapers ativos (ex: scrap_semae_piracicaba, scrap_llz_condominio)
    raw_scrapers = os.getenv("SCRAPERS_ATIVOS", "")
    LISTA_FUNCOES_SCRAPERS = [s.strip() for s in raw_scrapers.split(",") if s.strip()]

    # --- TELEGRAM ---
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    # IDs permitidos (convertidos para int para o middleware de segurança)
    raw_allowed = os.getenv("ALLOWED_USERS", "")
    ALLOWED_USERS = [int(u.strip()) for u in raw_allowed.split(",") if u.strip()]

    # IDs específicos para identificação de rateio
    ID_NEKO = os.getenv("ID_NEKO")
    ID_BAKA = os.getenv("ID_BAKA")

    # --- GOOGLE SHEETS E FINANCEIRO ---
    SHEET_NAME = os.getenv("SHEET_NAME", "Contas - Casa")
    MAPA_CATEGORIAS = os.getenv("MAPA_CATEGORIAS")

    # Taxas de Rateio
    RATEIO_NEKO = float(os.getenv("RATEIO_NEKO", "0.475"))
    RATEIO_BAKA = float(os.getenv("RATEIO_BAKA", "0.525"))

    # Categorias para o menu de lançamento manual
    raw_manuais = os.getenv("CATEGORIAS_MANUAIS", "Lazer,Mercado,Carro,Meninas")
    CATEGORIAS_MANUAIS = [c.strip() for c in raw_manuais.split(",") if c.strip()]


# Garante que o diretório temporário para PDFs exista
if not os.path.exists(Config.TEMP_DIR):
    os.makedirs(Config.TEMP_DIR)