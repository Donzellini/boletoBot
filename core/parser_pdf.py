import pdfplumber
import re


def extrair_dados_pdf(pdf_path, password=None):
    """Extrai linha digitável de qualquer PDF, com ou sem senha."""
    regex_boleto = r'(\d{5}[\.\s]?\d{5}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d[\.\s]?\d{14})|(\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d)'

    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            texto = "".join([p.extract_text() for p in pdf.pages])
            match = re.search(regex_boleto, texto)
            if match:
                # Retorna apenas os números limpos
                return re.sub(r'\D', '', match.group(0))
    except Exception as e:
        print(f"Erro ao ler PDF {pdf_path}: {e}")
    return None
