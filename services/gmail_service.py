import re
import os
from datetime import date, timedelta
from imap_tools import MailBox, AND

from core.logger import logger
from core.models import Boleto
from core.config import Config
from utils.helpers import extrair_mes_referencia
from utils.extractor import extrair_dados_de_texto
from utils.parser_pdf import extrair_dados_pdf
from utils.web_downloader import baixar_boleto_bevi


def buscar_faturas_email():
    boletos_encontrados = []
    data_busca = date(date.today().year, date.today().month, 1) - timedelta(days=7)

    with MailBox('imap.gmail.com').login(Config.GMAIL_USER, Config.GMAIL_PASS) as mailbox:
        for label in Config.LABELS_INTERESSE:
            if not mailbox.folder.exists(label):
                continue

            mailbox.folder.set(label)
            logger.info(f"📩 Verificando label: {label}")

            for msg in mailbox.fetch(AND(date_gte=data_busca)):
                # Limpa o corpo removendo caracteres de HTML que quebram regex
                corpo = (msg.text + msg.html).replace('\xa0', ' ')

                # 1. Usa o helper para definir o mês (prioriza Vencimento)
                mes_ref = extrair_mes_referencia(corpo)

                # 2. Usa o EXTRATOR CENTRAL para pegar Linha, Pix e Valor de uma vez
                dados = extrair_dados_de_texto(corpo)

                novo_boleto = Boleto(
                    origem=label,
                    titulo=msg.subject,
                    mes_referencia=mes_ref,
                    valor=dados["valor"],
                    linha_digitavel=dados["linha"],
                    pix=dados["pix"]
                )

                # --- LÓGICA DE APOIO: Se o corpo não bastou, tenta links/anexos ---

                # Caso Bevi/Aluguel (Links Externos)
                if ("aluguel" in label.lower() or "bevi" in label.lower()) and not novo_boleto.linha_digitavel:
                    links = re.findall(r'href=[\'"]?([^\'" >]+)', msg.html)
                    for link in links:
                        if "cobranca" in link or "pagamento" in link:
                            path = baixar_boleto_bevi(link)
                            if path:
                                dados_pdf = extrair_dados_pdf(path)
                                if dados_pdf["linha"]: novo_boleto.linha_digitavel = dados_pdf["linha"]
                                if dados_pdf["valor"]: novo_boleto.valor = dados_pdf["valor"]
                                if dados_pdf.get("mes_referencia"): novo_boleto.mes_referencia = dados_pdf[
                                    "mes_referencia"]

                # Caso Geral (Anexos PDF)
                if not novo_boleto.linha_digitavel and not novo_boleto.pix:
                    for att in msg.attachments:
                        if att.filename.lower().endswith('.pdf'):
                            path = os.path.join(Config.TEMP_DIR, att.filename)
                            with open(path, 'wb') as f:
                                f.write(att.payload)

                            senha = Config.CPF_SENHA if "comgas" in label.lower() else None
                            dados_pdf = extrair_dados_pdf(path, password=senha)

                            if dados_pdf["linha"]: novo_boleto.linha_digitavel = dados_pdf["linha"]
                            if dados_pdf["pix"]: novo_boleto.pix = dados_pdf["pix"]
                            if dados_pdf["valor"]: novo_boleto.valor = dados_pdf["valor"]

                # Se encontrou forma de pagamento, valida e adiciona
                if novo_boleto.linha_digitavel or novo_boleto.pix:
                    logger.info(f"✅ Boleto identificado: {label} ({mes_ref})")
                    boletos_encontrados.append(novo_boleto)

    return boletos_encontrados