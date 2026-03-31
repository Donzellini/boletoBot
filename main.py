import os
import logging
import threading
from flask import Flask, request, jsonify
from flasgger import Flasgger
from telebot import types

import services.scrapers as scrapers_module
from core.config import Config
from core.database import inicializar_db, salvar_boleto_db
from services.gmail_service import buscar_faturas_email
from services.notification_service import enviar_notificacao_fatura, bot
from utils.helpers import exibir_resultado_extracao, logger

# Inicializa Flask
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Inicializa Swagger/Flasgger
swagger = Flasgger(app)

# Flag para evitar múltiplas inicializações
_webhook_initialized = False


def inicializar_webhook():
    """Registra o webhook no Telegram na primeira execução."""
    global _webhook_initialized
    
    if _webhook_initialized:
        return
    
    _webhook_initialized = True
    inicializar_db()
    
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    logger.info(f"📋 WEBHOOK_URL configurada: {WEBHOOK_URL if WEBHOOK_URL else '❌ NÃO CONFIGURADA'}")
    
    if WEBHOOK_URL:
        try:
            logger.info(f"🔗 Removendo webhook antigo (fallback para polling)...")
            bot.remove_webhook()
            logger.info("✅ Webhook removido. Usando polling como fallback.")
            
        except Exception as e:
            logger.error(f"❌ Erro ao remover webhook: {e}")
    
    # Inicia thread de polling em background
    iniciar_polling_background()


def iniciar_polling_background():
    """Inicia polling em thread separada para não bloquear Flask."""
    def polling_thread():
        logger.info("🤖 Iniciando BoletoBot via polling...")
        try:
            bot.polling(non_stop=True, timeout=30)
        except Exception as e:
            logger.error(f"❌ Erro no polling: {e}")
    
    thread = threading.Thread(target=polling_thread, daemon=True)
    thread.start()
    logger.info("✅ Thread de polling iniciada em background")


# Hook que roda antes do primeiro request
@app.before_request
def setup():
    """Executa uma vez antes do primeiro request."""
    inicializar_webhook()


def executar_ciclo_coleta(solicitante_id=None):
    """
    Orquestra a busca de boletos: varre Gmail, executa scrapers web,
    salva no banco de dados e notifica o usuário no Telegram.
    """
    try:
        # 1. Garante que o banco de dados e tabelas existam
        inicializar_db()
        logger.info("🚀 Iniciando ciclo de coleta de faturas...")

        # 2. Busca faturas no Gmail (PDFs e links)
        lista_faturas = buscar_faturas_email()
        # lista_faturas = []

        # 3. Executa Scrapers Web configurados no .env
        if Config.LISTA_FUNCOES_SCRAPERS:
            for nome_funcao in Config.LISTA_FUNCOES_SCRAPERS:
                try:
                    funcao_alvo = getattr(scrapers_module, nome_funcao, None)
                    if funcao_alvo and callable(funcao_alvo):
                        logger.info(f"🔎 Rodando scraper: {nome_funcao}")
                        resultado = funcao_alvo()
                        if resultado:
                            lista_faturas.append(resultado)
                except Exception as e:
                    logger.error(f"❌ Erro ao executar scraper {nome_funcao}: {e}")

        # 4. Processamento de Resultados
        if not lista_faturas:
            logger.info("Empty: Nenhum boleto novo encontrado.")
        else:
            for fatura in lista_faturas:
                # Exibe no console/logs para monitoramento
                exibir_resultado_extracao(fatura)

                # Salva no banco (retorna True se for um boleto novo/inédito)
                if salvar_boleto_db(fatura):
                    enviar_notificacao_fatura(fatura, target_user=solicitante_id)
                else:
                    logger.info(f"⏭️ Ignorando duplicata: {fatura.titulo}")

        logger.info("✅ Ciclo de coleta finalizado.")

    except Exception as e:
        logger.error(f"💥 Erro crítico no ciclo de coleta: {e}")


# --- WEBHOOK ENDPOINT ---
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Recebe updates do Telegram via webhook
    ---
    tags:
      - Webhook
    parameters:
      - in: body
        name: update
        description: Update do Telegram
        required: true
        schema:
          type: object
    responses:
      200:
        description: Update processado com sucesso
      500:
        description: Erro ao processar update
    """
    try:
        json_data = request.get_json()
        update = types.Update(data=json_data)
        bot.process_new_updates([update])
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    """Página inicial com documentação dos endpoints"""
    return jsonify({
        "app": "BoletoBot",
        "status": "online",
        "mode": "polling (background thread)",
        "endpoints": {
            "GET /": "Esta página",
            "GET /health": "Health check",
            "POST /webhook": "Recebe updates do Telegram",
            "POST /webhook-register": "Re-registra webhook manualmente",
            "GET /webhook-info": "Info sobre status do webhook"
        },
        "telegram_bot": "@BoletoBot",
        "last_updated": "2026-03-29"
    }), 200


@app.route('/health', methods=['GET'])
def health():
    """
    Health check para Fly.io
    ---
    tags:
      - Health
    responses:
      200:
        description: API está saudável
        schema:
          properties:
            status:
              type: string
              example: healthy
    """
    return jsonify({"status": "healthy"}), 200


@app.route('/webhook-register', methods=['POST'])
def webhook_register():
    """
    Re-registra webhook manualmente
    ---
    tags:
      - Webhook
    responses:
      200:
        description: Webhook registrado com sucesso
      400:
        description: WEBHOOK_URL não configurada
      500:
        description: Erro ao registrar webhook
    """
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    logger.info(f"📋 [WEBHOOK-REGISTER] WEBHOOK_URL: {WEBHOOK_URL if WEBHOOK_URL else '❌ NÃO CONFIGURADA'}")
    
    if not WEBHOOK_URL:
        return jsonify({"error": "WEBHOOK_URL not configured"}), 400
    
    try:
        logger.info(f"🔗 [MANUAL] Registrando webhook em {WEBHOOK_URL}")
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        logger.info("✅ [MANUAL] Webhook registrado com sucesso!")
        
        # Verificar status
        webhook_info = bot.get_webhook_info()
        info = {
            "status": "webhook registered",
            "url": webhook_info.url,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "pending_update_count": webhook_info.pending_update_count,
            "last_error_message": webhook_info.last_error_message if webhook_info.last_error_date else None
        }
        return jsonify(info), 200
    except Exception as e:
        logger.error(f"❌ Erro ao configurar webhook: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/webhook-info', methods=['GET'])
def webhook_info():
    """
    Verifica status do webhook no Telegram
    ---
    tags:
      - Webhook
    responses:
      200:
        description: Informações do webhook
      500:
        description: Erro ao obter informações
    """
    try:
        info = bot.get_webhook_info()
        return jsonify({
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date,
            "last_error_message": info.last_error_message if info.last_error_date else None,
            "max_connections": info.max_connections
        }), 200
    except Exception as e:
        logger.error(f"❌ Erro ao obter webhook info: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Fallback: Se rodar localmente com python main.py
    inicializar_webhook()
    
    logger.info("🤖 BoletoBot Online com polling (Gunicorn + background thread)")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8000)), debug=False)