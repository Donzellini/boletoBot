import re
import os
from datetime import date, timedelta
from imap_tools import MailBox, AND
from core.models import Boleto
from core.config import Config
from utils.parser_pdf import extrair_dados_de_texto, extrair_dados_pdf
from utils.web_downloader import baixar_boleto_bevi


def buscar_faturas_email():
    boletos_encontrados = []
    data_busca = date(date.today().year, date.today().month, 1) - timedelta(days=7)

    with MailBox('imap.gmail.com').login(Config.GMAIL_USER, Config.GMAIL_PASS) as mailbox:
        for label in Config.LABELS_INTERESSE:
            mailbox.folder.set(label)

            for msg in mailbox.fetch(AND(date_gte=data_busca)):
                mes_ref = msg.date.strftime("%m/%Y")
                novo_boleto = Boleto(origem=label, titulo=msg.subject, mes_referencia=mes_ref)

                # --- PASSO 1: Extração do CORPO (Texto/HTML) ---
                corpo = (msg.text + msg.html)
                # O cerne: tratamos o corpo como um "documento" e extraímos o dicionário
                dados_corpo = extrair_dados_de_texto(corpo)

                novo_boleto.linha_digitavel = dados_corpo["linha"]
                novo_boleto.pix = dados_corpo["pix"]
                novo_boleto.valor = dados_corpo["valor"]

                # --- PASSO 2: Links Externos (Bevi) ---
                if ("aluguel" in label.lower() or "bevi" in label.lower()) and not novo_boleto.linha_digitavel:
                    links = re.findall(r'href=[\'"]?([^\'" >]+)', msg.html)
                    for link in links:
                        if "cobranca" in link or "pagamento" in link:
                            path = baixar_boleto_bevi(link)
                            if path:
                                dados_bevi = extrair_dados_pdf(path)
                                # Atualiza apenas se o PDF trouxer dados novos
                                if dados_bevi["linha"]: novo_boleto.linha_digitavel = dados_bevi["linha"]
                                if dados_bevi["valor"]: novo_boleto.valor = dados_bevi["valor"]

                # --- PASSO 3: Anexos PDF ---
                if not novo_boleto.linha_digitavel and not novo_boleto.pix:
                    for att in msg.attachments:
                        if '.pdf' in att.filename.lower():
                            path = os.path.join(Config.TEMP_DIR, att.filename)
                            with open(path, 'wb') as f:
                                f.write(att.payload)

                            senha = Config.CPF_SENHA if "comgas" in label.lower() else None
                            dados_pdf = extrair_dados_pdf(path, password=senha)

                            # Preenche o objeto com o dicionário retornado
                            if dados_pdf["linha"]: novo_boleto.linha_digitavel = dados_pdf["linha"]
                            if dados_pdf["pix"]: novo_boleto.pix = dados_pdf["pix"]
                            if dados_pdf["valor"]: novo_boleto.valor = dados_pdf["valor"]

                boletos_encontrados.append(novo_boleto)
    return boletos_encontrados