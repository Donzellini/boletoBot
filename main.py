import services.scrapers as scrapers_module
from core.config import Config
from core.database import inicializar_db, salvar_boleto_db
from services.gmail_service import buscar_faturas_email
from services.notification_service import enviar_notificacao_fatura, bot
from utils.helpers import exibir_resultado, logger


def executar_ciclo_coleta():
    """
    Executa a parte de 'Inteligência' do Bot:
    Busca e-mails, roda scrapers e envia para o Telegram.
    """
    inicializar_db()
    logger.info("🚀 Iniciando Orquestração com Banco de Dados")

    # 1. Processar Gmail
    lista_faturas = buscar_faturas_email()

    # 2. Executar Scrapers dinâmicos (vimos no .env)
    if Config.LISTA_FUNCOES_SCRAPERS:
        for nome_funcao in Config.LISTA_FUNCOES_SCRAPERS:
            try:
                funcao_para_rodar = getattr(scrapers_module, nome_funcao, None)
                if funcao_para_rodar and callable(funcao_para_rodar):
                    logger.info(f"🔎 Rodando scraper: {nome_funcao}")
                    resultado = funcao_para_rodar()
                    if resultado:
                        lista_faturas.append(resultado)
                else:
                    logger.warning(f"⚠️ Função {nome_funcao} não encontrada em scrapers.py")
            except Exception as e:
                logger.error(f"❌ Erro ao executar {nome_funcao}: {e}")

    # 3. Enviar resultados para o Telegram
    if not lista_faturas:
        logger.info("Empty: Nenhum boleto novo encontrado nesta rodada.")
    else:
        for fatura in lista_faturas:
            exibir_resultado(fatura)
            foi_salvo = salvar_boleto_db(fatura)
            if foi_salvo:
                enviar_notificacao_fatura(fatura)
            else:
                logger.info(f"⏭️ Ignorando duplicata: {fatura.titulo}")

    logger.info("✅ Ciclo de coleta finalizado.")


if __name__ == "__main__":
    # 1. Rodar a coleta uma vez ao iniciar
    executar_ciclo_coleta()

    # 2. Iniciar o Bot em modo de escuta (Polling)
    # Isso permite que o Gatekeeper e os botões interativos funcionem
    logger.info("🤖 Bot em modo interativo. Aguardando comandos...")
    bot.polling(non_stop=True)