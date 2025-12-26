import pdfplumber
from utils.extractor import extrair_dados_de_texto


def extrair_dados_pdf(pdf_path, password=None):
    """
    Abre o PDF, extrai o conteúdo textual e utiliza o extrator universal
    para identificar Linha Digitável, PIX e Valor.
    """
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            # Consolida o texto de todas as páginas do documento
            texto_completo = "".join([p.extract_text() for p in pdf.pages if p.extract_text()])

            # Delega a inteligência de busca para o extrator central
            return extrair_dados_de_texto(texto_completo)

    except Exception as e:
        print(f"❌ Erro ao ler PDF {pdf_path}: {e}")
        return {"linha": None, "pix": None, "valor": None}