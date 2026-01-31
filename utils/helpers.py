import re
from datetime import datetime

from core.logger import logger


def exibir_resultado_extracao(boleto):
    """
    Exibe um resumo elegante no console sempre que um boleto é processado.
    Útil para debug e acompanhamento manual.
    """
    print("\n" + "═" * 60)
    logger.info(f"📄 FATURA: {boleto.titulo}")
    logger.info(f"📂 ORIGEM: {boleto.origem}")
    logger.info(f"💸 VALOR EXTRAÍDO: R$ {boleto.valor if boleto.valor else '---'}")

    if boleto.pix:
        # Exibe apenas o início do PIX para não poluir o console
        logger.info(f"✨ PIX DETECTADO: {boleto.pix[:30]}...")

    if boleto.linha_digitavel:
        logger.info(f"🔢 LINHA: {boleto.linha_digitavel}")

    if not any([boleto.pix, boleto.linha_digitavel]):
        logger.warning("⚠️ Atenção: Nenhum dado de pagamento identificado.")

    print("═" * 60 + "\n")


def formatar_moeda_brasileira(valor_float):
    """Auxiliar simples para exibir valores formatados no console ou logs."""
    return "{:,.2f}".format(valor_float).replace(',', 'v').replace('.', ',').replace('v', '.')


def formatar_mensagem_boleto(boleto):
    """Lê os dados do dicionário/sqlite3.Row usando chaves."""
    pago_via = "💠 PIX" if boleto['pix'] else "📑 Linha Digitável"
    conteudo = boleto['pix'] if boleto['pix'] else boleto['linha_digitavel']

    return (
        f"🚨 *Fatura Pendente Encontrada!* \n\n"
        f"🏷️ *Origem:* {boleto['origem']}\n"
        f"📝 *Título:* {boleto['titulo']}\n"
        f"📄 *Mês Referência:* {boleto['mes_referencia']}\n"
        f"💰 *Valor:* R$ {boleto['valor'] if boleto['valor'] else 'Não identificado'}\n"
        f"💳 *Método:* {pago_via}\n\n"
        f"`{conteudo}`"
    )


def extrair_mes_referencia(texto):
    """
    Extrai o mês/ano baseado na DATA DE VENCIMENTO.
    Focado em garantir que o lançamento caia no mês do pagamento.
    """
    if not texto:
        return datetime.now().strftime("%m/%Y")

    # Sanitização: Remove espaços excessivos e quebras de linha que grudam no PIX
    texto_limpo = re.sub(r'\s+', ' ', texto).replace('\xa0', ' ')

    # 1. Busca por 'Vencimento' ou 'Vence em'
    # Ajustei a regex para aceitar o texto colado (Vencimento09/02/2026)
    # e validar que o ano comece com '20' (evita o erro 2652)
    match_venc = re.search(r'(?:Vencimento|Vence|Venc)[:\s]*(\d{2})[./](\d{2})[./](20\d{2})', texto_limpo, re.IGNORECASE)
    if match_venc:
        return f"{match_venc.group(2)}/{match_venc.group(3)}"

    # 2. Busca genérica de data (DD/MM/YYYY) mas validando o século
    # Isso evita pegar sequências numéricas aleatórias de protocolos
    datas_encontradas = re.findall(r'(\d{2})[./](\d{2})[./](20\d{2})', texto_limpo)
    if datas_encontradas:
        # Pegamos a primeira data válida encontrada como vencimento provável
        _, mes, ano = datas_encontradas[0]
        return f"{mes}/{ano}"

    # Fallback: Mês atual
    return datetime.now().strftime("%m/%Y")
