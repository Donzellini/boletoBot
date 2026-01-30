import re
import os
from datetime import date, timedelta
from imap_tools import MailBox, AND

from core.logger import logger
from core.models import Boleto
from core.config import Config
from utils.helpers import extrair_mes_referencia
from utils.parser_pdf import extrair_dados_de_texto, extrair_dados_pdf
from utils.web_downloader import baixar_boleto_bevi


def buscar_faturas_email():
    boletos_encontrados = []
    data_busca = date(date.today().year, date.today().month, 1) - timedelta(days=7)

    with MailBox('imap.gmail.com').login(Config.GMAIL_USER, Config.GMAIL_PASS) as mailbox:
        for label in Config.LABELS_INTERESSE:
            mailbox.folder.set(label)
            logger.info(f"📩 Verificando label: {label}")

            for msg in mailbox.fetch(AND(date_gte=data_busca)):
                corpo = (msg.text + msg.html)

                # 1. Identifica o mês de referência (Prioriza data de Vencimento no corpo)
                mes_ref = extrair_mes_referencia(corpo)

                # Criamos o objeto base
                novo_boleto = Boleto(origem=label, titulo=msg.subject, mes_referencia=mes_ref)

                # --- LÓGICA ESPECÍFICA: LLZ / CONDOMÍNIO ---
                if "condominio" in label.lower() or "llz" in corpo.lower():
                    logger.info("🏠 Extraindo dados diretos do e-mail da LLZ...")

                    # Valor: R$ 357,07 -> 357.07
                    valor_match = re.search(r'R\$\s*(\d+,\d{2})', corpo)
                    if valor_match:
                        novo_boleto.valor = valor_match.group(1).replace(',', '.')

                    # Linha Digitável: sequência de 47-48 dígitos
                    linha_match = re.search(r'\d{47,48}', corpo)
                    if linha_match:
                        novo_boleto.linha_digitavel = linha_match.group(0)

                    # Se já pegamos o que importa no corpo, salvamos e pulamos para o próximo e-mail
                    if novo_boleto.linha_digitavel or novo_boleto.pix:
                        boletos_encontrados.append(novo_boleto)
                        continue

                # --- LÓGICA GERAL: Extração de Texto do Corpo ---
                dados_corpo = extrair_dados_de_texto(corpo)
                if not novo_boleto.linha_digitavel: novo_boleto.linha_digitavel = dados_corpo["linha"]
                if not novo_boleto.pix: novo_boleto.pix = dados_corpo["pix"]
                if not novo_boleto.valor: novo_boleto.valor = dados_corpo["valor"]

                # --- PASSO 2: Links Externos (Bevi/Aluguel) ---
                if ("aluguel" in label.lower() or "bevi" in label.lower()) and not novo_boleto.linha_digitavel:
                    links = re.findall(r'href=[\'"]?([^\'" >]+)', msg.html)
                    for link in links:
                        if "cobranca" in link or "pagamento" in link:
                            path = baixar_boleto_bevi(link)
                            if path:
                                dados_bevi = extrair_dados_pdf(path)
                                if dados_bevi.get("mes_referencia"):
                                    novo_boleto.mes_referencia = dados_bevi["mes_referencia"]
                                if dados_bevi["linha"]: novo_boleto.linha_digitavel = dados_bevi["linha"]
                                if dados_bevi["valor"]: novo_boleto.valor = dados_bevi["valor"]

                # --- PASSO 3: Anexos PDF (Comgas, etc) ---
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
                            if dados_pdf.get("mes_referencia"): novo_boleto.mes_referencia = dados_pdf["mes_referencia"]

                # Adiciona à lista final se tiver ao menos uma forma de pagamento
                if novo_boleto.linha_digitavel or novo_boleto.pix:
                    boletos_encontrados.append(novo_boleto)

    return boletos_encontrados