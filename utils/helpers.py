import re
import logging
import sys

# Configuração básica do Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("BoletoBot")


def exibir_resultado(boleto):
    """Print padronizado e elegante para os resultados finais."""
    print("\n" + "=" * 50)
    logger.info(f"📄 FATURA DETECTADA: {boleto.titulo}")
    logger.info(f"📂 ORIGEM: {boleto.origem}")
    logger.info(f"💸 VALOR: {boleto.valor}")

    if boleto.pix:
        logger.info(f"✨ PIX: {boleto.pix[:40]}...")
    if boleto.linha_digitavel:
        logger.info(f"🔢 LINHA: {boleto.linha_digitavel}")

    if not any([boleto.pix, boleto.linha_digitavel]):
        logger.warning("⚠️ Nenhum dado de pagamento extraído.")
    print("=" * 50)