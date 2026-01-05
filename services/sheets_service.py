import re
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from core.config import Config
from core.logger import logger

# Caminho para as credenciais do Google Cloud
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')


def obter_aba_mensal(spreadsheet, mes_alvo=None):
    """
    Localiza a aba do mês atual (MM/AAAA).
    Se não existir, cria uma nova duplicando a aba de índice 0 como modelo.
    """
    mes_alvo = mes_alvo if mes_alvo else datetime.now().strftime("%m/%Y")
    try:
        return spreadsheet.worksheet(mes_alvo)
    except gspread.exceptions.WorksheetNotFound:
        logger.info(f"✨ Criando nova aba para o mês {mes_alvo}...")
        abas = spreadsheet.worksheets()
        aba_modelo = abas[0]  # template

        nova_aba = spreadsheet.duplicate_sheet(
            source_sheet_id=aba_modelo.id,
            insert_sheet_index=0,
            new_sheet_name=mes_alvo
        )
        return nova_aba


def conectar_sheets(mes_alvo=None):
    """Configura a conexão com a API do Google Sheets."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)
    ss = client.open(Config.SHEET_NAME)
    return obter_aba_mensal(ss, mes_alvo)


def atualizar_valor_planilha(item_nome, valor_str, mes_referencia=None):
    """
    Atualiza o valor de um boleto automático na planilha.
    Converte para o formato '1234,56' para evitar erros de validação.
    """
    try:
        mes_alvo = mes_referencia if mes_referencia else datetime.now().strftime("%m/%Y")
        aba = conectar_sheets(mes_alvo)

        # Limpeza para garantir formato numérico (Ex: R$ 1.234,56 -> 1234.56)
        valor_limpo = valor_str.replace('R$', '').replace('.', '').replace(',', '.').strip()
        valor_float = float(valor_limpo)
        valor_fmt = "{:.2f}".format(valor_float).replace('.', ',')

        # Mapeamento de nomes (Ex: 'Finances/Claro' -> 'CLARO')
        mapa = {k.strip().lower(): v.strip() for k, v in
                [item.split(':') for item in Config.MAPA_CATEGORIAS.split(',') if ':' in item]}

        nome_busca = item_nome
        for chave, real in mapa.items():
            if chave in item_nome.lower():
                nome_busca = real
                break

        celula = aba.find(re.compile(f"^{nome_busca}$", re.IGNORECASE))

        # Atualiza Valor (Col C) e Rateio Neko (Col E)
        aba.update_cell(celula.row, celula.col + 1, valor_fmt)

        valor_neko = "{:.2f}".format(valor_float * Config.RATEIO_NEKO).replace('.', ',')
        aba.update_cell(celula.row, celula.col + 2, valor_neko)

        logger.info(f"✅ Planilha: {nome_busca} atualizado para {valor_fmt}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar planilha: {e}")
        return False


def lancar_gasto_dinamico(categoria, item, valor_str, user_id, mes_referencia=None):
    """
    Insere gasto manual agrupando por categoria e calculando rateio por usuário.
    """
    try:
        mes_alvo = mes_referencia if mes_referencia else datetime.now().strftime("%m/%Y")
        aba = conectar_sheets(mes_alvo)
        cat_upper = categoria.upper()
        item_upper = item.upper()

        valor_float = float(valor_str)

        # Lógica de Rateio baseada em quem enviou (Neko ou Baka)
        if str(user_id) == Config.ID_NEKO:
            taxa_do_parceiro = Config.RATEIO_BAKA
            nome_parceiro = "BAKA"
        else:
            taxa_do_parceiro = Config.RATEIO_NEKO
            nome_parceiro = "NEKO"

        parte_parceiro = valor_float * taxa_do_parceiro

        val_fmt = "{:.2f}".format(valor_float).replace('.', ',')
        parc_fmt = "{:.2f}".format(parte_parceiro).replace('.', ',')

        # --- LÓGICA SELETIVA DE ATUALIZAÇÃO ---
        celula_existente = None
        # SÓ tenta atualizar se for a categoria FIANÇA
        if cat_upper == "CASA" and item_upper == "FIANÇA":
            try:
                celula_existente = aba.find(re.compile(f"^{item_upper}$", re.IGNORECASE), in_column=2)
            except:
                celula_existente = None

        if celula_existente:
            linha_alvo = celula_existente.row
            logger.info(f"🔄 Atualizando Fiança na linha {linha_alvo}")
        else:
            # Para outras categorias (Mercado, Lazer, etc) ou Fiança nova, INSERE linha
            celulas_cat = aba.findall(cat_upper, in_column=1)
            if celulas_cat:
                linha_alvo = celulas_cat[-1].row + 1
            else:
                valores_coluna_a = aba.col_values(1)
                linha_alvo = len(valores_coluna_a) + 1
                logger.info(f"📂 Nova categoria detectada ({cat_upper}). Alocando na linha {linha_alvo}")

            aba.insert_row([], linha_alvo)
            logger.info(f"➕ Inserindo novo gasto em {cat_upper}")

        aba.update_cell(linha_alvo, 1, cat_upper)
        aba.update_cell(linha_alvo, 2, item.upper())
        aba.update_cell(linha_alvo, 3, val_fmt)
        aba.update_cell(linha_alvo, 4, parc_fmt)

        return {
            "sucesso": True, "categoria": cat_upper, "item": item.upper(),
            "total": valor_float, "parte_parceiro": parte_parceiro, "nome_parceiro": nome_parceiro
        }
    except Exception as e:
        logger.error(f"❌ Erro no lançamento dinâmico: {e}")
        return {"sucesso": False}


def obter_resumo_financeiro():
    """Lê os totais da tabela auxiliar ao lado (G8:H10)."""
    try:
        mes_alvo = datetime.now().strftime("%m/%Y")
        aba = conectar_sheets(mes_alvo)
        return {
            "geral": aba.acell('G3').value,
            "baka": aba.acell('G4').value,
            "neko": aba.acell('G5').value
        }
    except Exception as e:
        logger.error(f"❌ Erro ao ler resumo: {e}")
        return None