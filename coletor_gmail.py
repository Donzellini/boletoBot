import os
import re
import pdfplumber
from datetime import date, timedelta

import requests
from dotenv import load_dotenv
from imap_tools import MailBox, AND

from parser_pdf import extrair_dados_pdf

load_dotenv()

# Configurações do .env
raw_labels = os.getenv("LABELS_INTERESSE", "")
LABELS_INTERESSE = [str(u.strip()) for u in raw_labels.split(",") if u.strip()]
SENHA_PDF_COMGAS = os.getenv("CPF_SENHA")  # 3 primeiros dígitos do CPF
TEMP_DIR = '/tmp/boleto_bot'


def limpar_codigo(texto):
    """Remove espaços, pontos e caracteres não numéricos"""
    if not texto: return None
    return re.sub(r'\D', '', texto)


def extrair_pix(texto):
    """Busca o padrão Pix Copia e Cola (BRCode)"""
    # Geralmente começa com 000201
    regex_pix = r'000201[a-zA-Z0-9]+'
    match = re.search(regex_pix, texto)
    return match.group(0) if match else None


def extrair_linha_digitavel(texto):
    """Busca sequências de 47 ou 48 dígitos (com ou sem formatação)"""
    # Regex para boletos bancários (47 dígitos) ou tributos/concessionárias (48 dígitos)
    regex_boleto = r'(\d{5}[\.\s]?\d{5}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d[\.\s]?\d{14})|(\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d)'
    match = re.search(regex_boleto, texto)
    return limpar_codigo(match.group(0)) if match else None


def baixar_boleto_bevi(url_bevi):
    """Tenta baixar o PDF da Bevi via requests GET"""
    file_path = os.path.join(TEMP_DIR, "Finances_Aluguel_Bevi_Download.pdf")
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        print(f"  📡 Solicitando PDF Bevi...")
        response = requests.get(url_bevi, headers=headers, timeout=15)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', '').lower():
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path
    except Exception as e:
        print(f"  ❌ Falha no download Bevi: {e}")
    return None


def processar_email():
    USER = os.getenv('GMAIL_USER')
    PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

    # Filtro de data: 7 dias antes do início do mês para pegar Claro/Comgás antecipados
    data_busca = date(date.today().year, date.today().month, 1) - timedelta(days=7)

    with MailBox('imap.gmail.com').login(USER, PASSWORD) as mailbox:
        for label in LABELS_INTERESSE:
            print(f"\n📂 Lendo label: {label}")
            mailbox.folder.set(label)

            for msg in mailbox.fetch(AND(date_gte=data_busca)):
                resultado = {
                    "label": label,
                    "assunto": msg.subject,
                    "pix": None,
                    "linha_digitavel": None,
                    "link_bevi": None
                }

                # 1. TENTA NO CORPO DO EMAIL (Texto e HTML)
                corpo_total = (msg.text + msg.html)
                resultado["pix"] = extrair_pix(corpo_total)
                resultado["linha_digitavel"] = extrair_linha_digitavel(corpo_total)

                # 2. Lógica Bevi (Link Externo)
                if "aluguel" in label.lower() or "bevi" in label.lower():
                    links = re.findall(r'href=[\'"]?([^\'" >]+)', msg.html)
                    for link in links:
                        if "cobranca" in link or "pagamento" in link:
                            resultado["link_bevi"] = link
                            # Tenta baixar o boleto imediatamente
                            caminho_pdf = baixar_boleto_bevi(link)
                            if caminho_pdf:
                                texto_bevi = extrair_dados_pdf(caminho_pdf)
                                resultado["linha_digitavel"] = extrair_linha_digitavel(texto_bevi)

                # 3. SE NÃO ACHOU NO CORPO, TENTA NO PDF
                if not resultado["pix"] and not resultado["linha_digitavel"]:
                    for att in msg.attachments:
                        if '.pdf' in att.filename.lower():
                            file_path = f"/tmp/{att.filename}"
                            with open(file_path, 'wb') as f:
                                f.write(att.payload)

                            try:
                                # Se for Comgás, usa a senha do .env
                                password = SENHA_PDF_COMGAS if "comgas" in label.lower() else None
                                with pdfplumber.open(file_path, password=password) as pdf:
                                    texto_pdf = "".join([p.extract_text() for p in pdf.pages])
                                    resultado["linha_digitavel"] = extrair_linha_digitavel(texto_pdf)
                            except Exception as e:
                                print(f"  ❌ Erro no PDF {att.filename}: {e}")

                # PRINT FINAL DO QUE FOI ACHADO
                exibir_resultado(resultado)


def exibir_resultado(res):
    print(f"📧 {res['assunto']}")
    if res['pix']: print(f"  ✨ PIX: {res['pix'][:30]}...")
    if res['linha_digitavel']: print(f"  🔢 Linha: {res['linha_digitavel']}")
    if res['link_bevi']: print(f"  🔗 Link Bevi: {res['link_bevi']}")
    if not any([res['pix'], res['linha_digitavel'], res['link_bevi']]):
        print("  ⚠️ Nada encontrado.")


if __name__ == "__main__":
    processar_email()
