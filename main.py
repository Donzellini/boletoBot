import time

import services.scrapers as scrapers_module
from core.config import Config
from core.database import inicializar_db, salvar_boleto_db
from services.gmail_service import buscar_faturas_email
from services.notification_service import enviar_notificacao_fatura, bot
from utils.helpers import exibir_resultado_extracao, logger


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


if __name__ == "__main__":
    inicializar_db()
    logger.info("🤖 BoletoBot Online e aguardando comandos...")

    while True:
        try:
            bot.polling(non_stop=True, interval=2, timeout=60)
        except Exception as e:
            logger.error(f"⚠️ Erro no polling detectado: {e}. Tentando reconectar em 15s...")
            time.sleep(15)