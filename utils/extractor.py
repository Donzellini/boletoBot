import re
import pdfplumber

def extrair_dados_de_texto(texto):
    """
    Inteligência central: recebe qualquer string (corpo de email ou texto de PDF)
    e retorna o dicionário padronizado.
    """
    # Regexes
    regex_ld = r'(\d{5}[\.\s]?\d{5}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d[\.\s]?\d{14})|(\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d)'
    regex_valor = r'R\$\s?(\d{1,3}(?:\.\d{3})*,\d{2})'
    regex_pix = r'000201[\s\S]*?6304[A-Fa-f0-9]{4}'

    res = {"linha": None, "valor": None, "pix": None}

    if not texto:
        return res

    # 1. Busca Linha Digitável
    m_ld = re.search(regex_ld, texto)
    if m_ld: res["linha"] = re.sub(r'\D', '', m_ld.group(0))

    # 2. Busca Pix
    m_pix = re.search(regex_pix, texto)
    if m_pix: res["pix"] = re.sub(r'\s+', '', m_pix.group(0))

    # 3. Busca Valor (pega o último/maior encontrado)
    valores = re.findall(regex_valor, texto)
    if valores:
        res["valor"] = valores[-1].replace('.', '') # Formato "232,47"

    return res

def extrair_dados_pdf(pdf_path, password=None):
    """Apenas extrai o texto do PDF e passa para a função central."""
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            texto_completo = "".join([p.extract_text() for p in pdf.pages])
            return extrair_dados_de_texto(texto_completo)
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        return {"linha": None, "valor": None, "pix": None}
