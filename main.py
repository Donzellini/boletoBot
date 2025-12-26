import services.scrapers as scrapers_module
from core.config import Config
from services.gmail_service import buscar_faturas_email
from utils.helpers import exibir_resultado, logger


def executar_automacao():
    logger.info("🚀 Iniciando Orquestração Dinâmica via Reflexão")

    # 1. Processar Gmail
    logger.info("📧 Varrendo Gmail em busca de novas faturas...")
    lista_final = buscar_faturas_email()
    logger.info(f"✅ Gmail concluído: {len(lista_final)} itens encontrados.")

    # 2. Executar Scrapers dinâmicos
    if Config.LISTA_FUNCOES_SCRAPERS:
        logger.info(f"🌐 Verificando scrapers no .env: {Config.LISTA_FUNCOES_SCRAPERS}")

        for nome_funcao in Config.LISTA_FUNCOES_SCRAPERS:
            try:
                funcao_para_rodar = getattr(scrapers_module, nome_funcao, None)

                if funcao_para_rodar and callable(funcao_para_rodar):
                    logger.info(f"🔎 Executando scraper: {nome_funcao}")
                    resultado = funcao_para_rodar()
                    if resultado:
                        lista_final.append(resultado)
                else:
                    logger.error(f"❌ Função '{nome_funcao}' não encontrada em scrapers.py")

            except Exception as e:
                logger.critical(f"💥 Falha crítica em {nome_funcao}: {e}")

    # 3. Resultado Final
    logger.info(f"📊 Processamento finalizado. Total: {len(lista_final)} faturas.")
    for fatura in lista_final:
        exibir_resultado(fatura)


if __name__ == "__main__":
    executar_automacao()