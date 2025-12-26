import re
import os
from datetime import date, timedelta
from imap_tools import MailBox, AND
from core.models import Boleto
from core.config import Config
from core.parser_pdf import extrair_dados_pdf
from services.web_downloader import baixar_boleto_bevi


def buscar_faturas_email():
    boletos_encontrados = []
    data_busca = date(date.today().year, date.today().month, 1) - timedelta(days=7)

    with MailBox('imap.gmail.com').login(Config.GMAIL_USER, Config.GMAIL_PASS) as mailbox:
        for label in Config.LABELS_INTERESSE:
            mailbox.folder.set(label)
            for msg in mailbox.fetch(AND(date_gte=data_busca)):
                # Criamos a base do objeto
                novo_boleto = Boleto(origem=label, titulo=msg.subject)
                corpo = (msg.text + msg.html)

                # 1. Busca Pix e Linha no corpo
                regex_pix = r'000201[\s\S]*?6304[A-Fa-f0-9]{4}'
                match_pix = re.search(regex_pix, corpo)
                if match_pix: novo_boleto.pix = match_pix.group(0)

                # Regex Linha Digitável
                regex_ld = r'(\d{5}[\.\s]?\d{5}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d{5}[\.\s]?\d{6}[\.\s]?\d[\.\s]?\d{14})|(\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d[\-\s]?\d{11}[\-\s]?\d)'
                match_ld = re.search(regex_ld, corpo)
                if match_ld: novo_boleto.linha_digitavel = match_ld.group(0)

                # 2. Lógica Bevi
                if "aluguel" in label.lower() or "bevi" in label.lower():
                    links = re.findall(r'href=[\'"]?([^\'" >]+)', msg.html)
                    for link in links:
                        if "cobranca" in link or "pagamento" in link:
                            novo_boleto.link_externo = link
                            path = baixar_boleto_bevi(link)
                            if path:
                                novo_boleto.linha_digitavel = extrair_dados_pdf(path)

                # 3. Anexos PDF
                if not novo_boleto.linha_digitavel and not novo_boleto.pix:
                    for att in msg.attachments:
                        if '.pdf' in att.filename.lower():
                            path = os.path.join(Config.TEMP_DIR, att.filename)
                            with open(path, 'wb') as f: f.write(att.payload)
                            senha = Config.CPF_SENHA if "comgas" in label.lower() else None
                            novo_boleto.linha_digitavel = extrair_dados_pdf(path, password=senha)

                boletos_encontrados.append(novo_boleto)

    return boletos_encontrados
