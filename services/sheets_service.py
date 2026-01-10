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
    Atualiza as contas fixas na planilha com lógica de compensação:
    - NEKO (Coluna D): Recebe a parte dele POSITIVA (Débito com a Baka).
    - BAKA (Coluna E): Recebe a parte dela NEGATIVA (Crédito, pois ela pagou o banco).
    """
    try:
        mes_alvo = mes_referencia if mes_referencia else datetime.now().strftime("%m/%Y")
        aba = conectar_sheets(mes_alvo)

        # 1. Limpeza para garantir formato numérico (Ex: R$ 1.234,56 -> 1234.56)
        valor_limpo = valor_str.replace('R$', '').replace('.', '').replace(',', '.').strip()
        valor_float = float(valor_limpo)

        # 2. Cálculo das partes (Baseado nas taxas de rateio)
        parte_neko = valor_float * Config.RATEIO_NEKO
        parte_baka = (valor_float * Config.RATEIO_BAKA) * -1  # Negativo pois a Baka pagou o boleto

        # 3. Formatação para o padrão brasileiro (vírgula)
        valor_fmt = "{:.2f}".format(valor_float).replace('.', ',')
        neko_fmt = "{:.2f}".format(parte_neko).replace('.', ',')
        baka_fmt = "{:.2f}".format(parte_baka).replace('.', ',')

        # 4. Mapeamento de nomes (Ex: 'Finances/Claro' -> 'CLARO')
        mapa = {k.strip().lower(): v.strip() for k, v in
                [item.split(':') for item in Config.MAPA_CATEGORIAS.split(',') if ':' in item]}

        nome_busca = item_nome
        for chave, real in mapa.items():
            if chave in item_nome.lower():
                nome_busca = real
                break

        # 5. Localização da célula e atualização em lote (Batch update para performance)
        celula = aba.find(re.compile(f"^{nome_busca}$", re.IGNORECASE))

        if celula:
            # Atualiza Coluna C (Valor Total), D (Neko) e E (Baka)
            aba.update_cell(celula.row, celula.col + 1, valor_fmt)  # Coluna C
            aba.update_cell(celula.row, celula.col + 2, neko_fmt)  # Coluna D
            aba.update_cell(celula.row, celula.col + 3, baka_fmt)  # Coluna E

            logger.info(f"✅ Fatura {nome_busca} atualizada: Neko (+{neko_fmt}) | Baka ({baka_fmt})")
            return True
        else:
            logger.warning(f"⚠️ Item '{nome_busca}' não encontrado na planilha.")
            return False
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

        # Determina quem pagou e calcula as partes
        if str(user_id) == Config.ID_NEKO:
            # NEKO pagou: recebe crédito da parte que a BAKA deve
            # A coluna do NEKO subtrai o que ele já adiantou
            parte_neko = (valor_float * Config.RATEIO_NEKO) * -1
            parte_baka = valor_float * Config.RATEIO_BAKA
            logger.info(f"💰 Lançamento: NEKO pagou, BAKA deve {parte_baka}")
        else:
            # BAKA pagou: recebe crédito da parte que o NEKO deve
            parte_baka = (valor_float * Config.RATEIO_BAKA) * -1
            parte_neko = valor_float * Config.RATEIO_NEKO
            logger.info(f"💰 Lançamento: BAKA pagou, NEKO deve {parte_neko}")

        val_neko_fmt = "{:.2f}".format(parte_neko).replace('.', ',')
        val_baka_fmt = "{:.2f}".format(parte_baka).replace('.', ',')

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

        aba.update_cell(linha_alvo, 1, cat_upper)  # Coluna A: Categoria
        aba.update_cell(linha_alvo, 2, item_upper)  # Coluna B: Item
        aba.update_cell(linha_alvo, 3, valor_str.replace('.', ','))  # Coluna C: Valor Total
        aba.update_cell(linha_alvo, 4, val_neko_fmt)  # Coluna D: Parte Neko
        aba.update_cell(linha_alvo, 5, val_baka_fmt)  # Coluna E: Parte Baka

        return {
            "sucesso": True, "categoria": cat_upper, "item": item_upper,
            "total": valor_float, "parte_neko": parte_neko, "parte_baka": parte_baka
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


def obter_gastos_detalhados():
    """
    Retorna uma lista de dicionários com todos os gastos do mês atual.
    """
    try:
        mes_alvo = datetime.now().strftime("%m/%Y")
        aba = conectar_sheets(mes_alvo)

        # Pega todos os valores da planilha
        # Assumindo que a estrutura é: A: Categoria, B: Item, C: Valor, D: Neko, E: Baka
        registros = aba.get_all_records()

        gastos = []
        for r in registros:
            # Filtra apenas linhas que tenham um valor preenchido
            if r.get('VALOR'):
                gastos.append({
                    'categoria': r.get('CATEGORIA', 'S/C'),
                    'item': r.get('ITEM', 'Sem Nome'),
                    'valor': r.get('VALOR'),
                    'neko': r.get('NEKO', '0,00'),
                    'baka': r.get('BAKA', '0,00')
                })
        return gastos
    except Exception as e:
        logger.error(f"❌ Erro ao buscar gastos detalhados: {e}")
        return None
