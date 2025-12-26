import re

def limpar_codigo(texto):
    if not texto: return None
    return re.sub(r'\D', '', texto)

def exibir_resultado(boleto):
    """Print padronizado para logs."""
    if boleto.pix: print(f"  ✨ PIX: {boleto.pix[:30]}...")
    if boleto.linha_digitavel: print(f"  🔢 Linha: {boleto.linha_digitavel}")
    if not any([boleto.pix, boleto.linha_digitavel]):
        print("  ⚠️ Nenhum dado de pagamento encontrado.")
