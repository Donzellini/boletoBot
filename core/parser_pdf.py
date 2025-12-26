import pdfplumber
import re


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

    # 2. Busca Pix
    match_pix = re.search(regex_pix, texto)
    if match_pix:
        res["pix"] = re.sub(r'\s+', '', match_pix.group(0))

    # 3. Busca Valor (Pega o último/maior encontrado no texto)
    valores = re.findall(regex_valor, texto)
    if valores:
        # Retorna formatado para o Sheets (ex: 232,47)
        res["valor"] = valores[-1].replace('.', '')

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