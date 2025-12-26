import re
from core.logger import logger

def extrair_valor_da_linha(linha):
    """
    Decodifica o valor diretamente da linha digitável.
    Suporta Boletos Bancários (final da linha) e Contas de Consumo (início da linha).
    """
    if not linha or len(linha) < 44:
        return None

    try:
        # CASO 1: Contas de Consumo/Tributos (Começa com 8)
        # O valor fica entre a 5ª e a 15ª posição
        if linha.startswith('8'):
            valor_str = linha[4:15]
            valor_float = int(valor_str) / 100.0
        # CASO 2: Boletos Bancários Comuns
        # O valor está nos últimos 10 dígitos
        else:
            valor_str = linha[-10:]
            valor_float = int(valor_str) / 100.0

        if valor_float > 0:
            # Retorna formatado com vírgula para o padrão brasileiro da planilha
            return "{:.2f}".format(valor_float).replace('.', ',')

    except Exception as e:
        logger.error(f"Erro ao decodificar valor da linha: {e}")
        return None
    return None

def extrair_dados_de_texto(texto):
    """
    Inteligência central: recebe qualquer string e retorna
    um dicionário padronizado com linha digitável, PIX e valor.
    """
    # Regexes otimizadas
    regex_ld = r'(\d{5}[\.\s]?\d{5}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d[\.\s]?\d{14})|(\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d)'
    regex_pix = r'000201[\s\S]*?6304[A-Fa-f0-9]{4}'
    regex_valor_rs = r'R\$\s?(\d{1,3}(?:\.\d{3})*,\d{2})'

    res = {"linha": None, "pix": None, "valor": None}

    if not texto:
        return res

    # 1. Busca Linha Digitável
    m_ld = re.search(regex_ld, texto)
    if m_ld:
        res["linha"] = re.sub(r'\D', '', m_ld.group(0))
        # Tenta extrair o valor matemático embutido na linha
        res["valor"] = extrair_valor_da_linha(res["linha"])

    # 2. Busca Pix Copia e Cola
    m_pix = re.search(regex_pix, texto)
    if m_pix:
        res["pix"] = re.sub(r'\s+', '', m_pix.group(0))

    # 3. Busca Valor por extenso (R$) se a linha digitável não informou o valor
    if not res["valor"]:
        valores_encontrados = re.findall(regex_valor_rs, texto)
        if valores_encontrados:
            # Estratégia: assume o último valor (geralmente o Total) e limpa pontos
            valor_final = valores_encontrados[-1].replace('.', '')
            res["valor"] = valor_final

    return res