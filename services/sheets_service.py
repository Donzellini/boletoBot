import re

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
from core.config import Config
from utils.helpers import logger


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')

def obter_aba_mensal(spreadsheet):
    """
    Busca a aba do mês atual. Se não existir, cria uma nova baseada na anterior.
    """
    mes_atual = datetime.now().strftime("%m/%Y")

    try:
        return spreadsheet.worksheet(mes_atual)
    except gspread.exceptions.WorksheetNotFound:
        logger.info(f"✨ Criando nova aba para o mês {mes_atual}...")

        # Pega a última aba disponível (teoricamente o mês anterior)
        # Ou você pode definir uma aba fixa chamada 'TEMPLATE'
        abas = spreadsheet.worksheets()
        aba_modelo = abas[8]  # Assume que a primeira aba é a mais recente ou o template

        nova_aba = spreadsheet.duplicate_sheet(
            source_sheet_id=aba_modelo.id,
            insert_sheet_index=0,
            new_sheet_name=mes_atual
        )
        # Opcional: Limpar os valores da nova aba mantendo apenas os títulos/categorias
        # Mas se for apenas atualizar as células, o gspread.find resolve.
        return nova_aba


def atualizar_valor_planilha(item_nome, valor_str):
    """
    item_nome: vem do bot (ex: 'Finances/Claro')
    valor_str: valor extraído (ex: '45,01')
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)

    try:
        ss = client.open(os.getenv("SHEET_NAME", "Contas - Casa"))
        aba = obter_aba_mensal(ss)

        # 1. Carrega o mapa do .env: {'claro': 'CLARO', 'comgás': 'COMGÁS', ...}
        raw_mapa = os.getenv("MAPA_CATEGORIAS", "")
        mapa = {k.strip().lower(): v.strip() for k, v in
                [item.split(':') for item in raw_mapa.split(',') if ':' in item]}

        # 2. Tenta encontrar qual chave do mapa está contida no item_nome
        # Se item_nome é 'Finances/Claro', ele vai achar a chave 'claro'
        nome_para_buscar = item_nome
        for termo_chave, nome_real_planilha in mapa.items():
            if termo_chave in item_nome.lower():
                nome_para_buscar = nome_real_planilha
                break

        logger.info(f"Busca na planilha traduzida: '{item_nome}' -> '{nome_para_buscar}'")

        # 3. Busca na planilha (agora com o nome limpo)
        try:
            # Usamos uma regex simples para ignorar Case Sensitive na planilha também
            celula = aba.find(re.compile(f"^{nome_para_buscar}$", re.IGNORECASE))

            valor_limpo = valor_str.replace('R$', '').replace('.', '').replace(',', '.').strip()
            valor_float = float(valor_limpo)
            valor_formatado_para_sheets = "{:.2f}".format(valor_float).replace('.', ',')
            aba.update_cell(celula.row, celula.col + 1, valor_formatado_para_sheets)

            logger.info(f"✅ Planilha atualizada: {nome_para_buscar} -> R$ {valor_float}")
            return True
        except gspread.IncorrectCellLabel:
            logger.warning(f"⚠️ Célula '{nome_para_buscar}' não encontrada na aba {aba.title}")
            return False

    except Exception as e:
        logger.error(f"❌ Erro ao acessar Sheets: {e}")
        return False


def lancar_gasto_dinamico(categoria_alvo, item_desc, valor_str, user_id):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)

    try:
        ss = client.open(os.getenv("SHEET_NAME", "Contas - Casa"))
        aba = obter_aba_mensal(ss)

        categoria_upper = categoria_alvo.upper()
        valor_float = float(valor_str.replace(',', '.'))

        # Identifica o rateio pelo ID do usuário
        is_neko = str(user_id) == os.getenv("ID_NEKO")
        taxa = float(os.getenv("RATEIO_BAKA")) if is_neko else float(os.getenv("RATEIO_NEKO"))
        valor_parte_parceiro = valor_float * taxa

        # 1. Busca todas as células da Coluna A para encontrar o grupo
        celulas_categoria = aba.findall(categoria_upper, in_column=1)

        if celulas_categoria:
            # Se a categoria já existe, insere logo após o último item do grupo
            linha_insercao = celulas_categoria[-1].row + 1
            logger.info(f"📍 Agrupando: {categoria_upper} será inserido na linha {linha_insercao}")
        else:
            linha_insercao = len(aba.get_all_values()) + 1
            logger.info(f"🆕 Nova Categoria: {categoria_upper} iniciando acima do Total Geral")

        # 2. Insere a linha e preenche os dados (Colunas A, B, C e D - agora que removeu a total categoria)
        aba.insert_row([], linha_insercao)

        aba.update_cell(linha_insercao, 1, categoria_upper)  # CATEGORIA
        aba.update_cell(linha_insercao, 2, item_desc.upper())  # ITENS

        fmt_total = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        fmt_neko = f"R$ {valor_parte_parceiro:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        aba.update_cell(linha_insercao, 3, fmt_total)  # VALOR
        aba.update_cell(linha_insercao, 4, fmt_neko)  # NEKO (Coluna D agora)

        return {
        "sucesso": True,
        "categoria": categoria_alvo.upper(),
        "item": item_desc.upper(),
        "total": valor_float,
        "parte_parceiro": valor_parte_parceiro,
        "nome_parceiro": "BAKA" if is_neko else "NEKO"
    }

    except Exception as e:
        logger.error(f"❌ Erro ao organizar gasto: {e}")
        return False


def obter_resumo_financeiro():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)
    ss = client.open(os.getenv("SHEET_NAME", "Contas - Casa"))
    aba = obter_aba_mensal(ss)

    # Busca os valores da sua tabela auxiliar (conforme o print image_db162a.png)
    total_geral = aba.acell('G8').value
    total_baka = aba.acell('G9').value
    total_neko = aba.acell('G10').value

    return {
        "geral": total_geral,
        "baka": total_baka,
        "neko": total_neko
    }

# --- BLOCO DE TESTE ---
if __name__ == "__main__":
    print("\n🧪 INICIANDO TESTE DE MANIPULAÇÃO DE PLANILHA")
    # Tenta atualizar a CPFL com um valor de teste
    # Certifique-se de que o nome 'CPFL' existe na sua coluna B!
    #resultado = atualizar_valor_planilha("CPFL", "250.90")
    resultado_2 = lancar_gasto_dinamico('MENINAS', 'Areia da Boa', '200.00')

    if resultado_2:
        print("🚀 TESTE CONCLUÍDO COM SUCESSO! Verifique seu Google Sheets.")
    else:
        print("verifique se o e-mail da Service Account tem permissão de Editor na planilha.")
