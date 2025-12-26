import pdfplumber
import re


def extrair_valor_da_linha(linha):
    """
    Decifra o valor diretamente da linha digitável.
    Suporta Boletos Bancários e Contas de Consumo (Claro, CPFL, etc).
    """
    if not linha or len(linha) < 44:
        return None

    try:
        # CASO 1: Contas de Consumo/Tributos (Começa com 8)
        # Ex: 8464000000029972... -> O valor está entre a 5ª e a 15ª posição
        if linha.startswith('8'):
            valor_str = linha[12:16]
            valor_float = int(valor_str) / 100.0

        # CASO 2: Boletos Bancários Comuns
        # O valor está nos últimos 10 dígitos
        else:
            valor_str = linha[-10:]
            valor_float = int(valor_str) / 100.0

        if valor_float > 0:
            return f"{valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    except Exception:
        return None
    return None


def extrair_dados_de_texto(texto):
    """
    Inteligência Central: Recebe qualquer string (corpo de email ou texto de PDF)
    e retorna o dicionário padronizado.
    """
    # Regex para Linha Digitável (Bancária e Tributos)
    regex_ld = r'(\d{5}[\.\s]?\d{5}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d[\.\s]?\d{14})|(\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d)'

    # Regex para Pix Copia e Cola (BRCode completo)
    regex_pix = r'000201[\s\S]*?6304[A-Fa-f0-9]{4}'

    # Regex para Valor Total (Padrão R$ 0,00)
    regex_valor = r'R\$\s?(\d{1,3}(?:\.\d{3})*,\d{2})'

    res = {"linha": None, "pix": None, "valor": None}

    if not texto:
        return res

    # 1. Busca Linha Digitável
    match_ld = re.search(regex_ld, texto)
    if match_ld:
        res["linha"] = re.sub(r'\D', '', match_ld.group(0))
        res["valor"] = extrair_valor_da_linha(res["linha"])

    # 2. Busca Pix
    match_pix = re.search(regex_pix, texto)
    if match_pix:
        res["pix"] = re.sub(r'\s+', '', match_pix.group(0))

    # 3. Busca Valor (Pega o último/maior encontrado no texto)
    if not res["valor"]:
        todos_valores = re.findall(regex_valor, texto)
        if todos_valores:
            # 1. Remove pontos de milhar para comparar numericamente
            valores_num = []
            for v in todos_valores:
                v_limpo = v.replace('.', '').replace(',', '.')
                try:
                    valores_num.append(float(v_limpo))
                except:
                    continue

            if valores_num:
                # Estratégia: O maior valor financeiro no boleto costuma ser o Total a Pagar
                maior_valor = max(valores_num)
                # Retorna formatado novamente para 1367,30
                res["valor"] = f"{maior_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    return res


def extrair_dados_pdf(pdf_path, password=None):
    """Extrai o texto do PDF e passa para o extrator universal."""
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            texto_completo = "".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            return extrair_dados_de_texto(texto_completo)
    except Exception as e:
        print(f"Erro ao ler PDF {pdf_path}: {e}")
        return {"linha": None, "pix": None, "valor": None}