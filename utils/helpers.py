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
