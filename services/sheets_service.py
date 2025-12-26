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
    Mapeia o item e atualiza o valor na aba do mês correto.
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)

    try:
        ss = client.open(os.getenv("SHEET_NAME", "Contas - Casa"))
        aba = obter_aba_mensal(ss)

        # Mapeamento via ENV (Ex: transforma 'CPFL PIRACICABA' em apenas 'CPFL')
        mapa = dict(item.split(':') for item in os.getenv("MAPA_CATEGORIAS", "").split(',') if ':' in item)

        nome_na_planilha = item_nome
        for termo_chave, nome_real in mapa.items():
            if termo_chave.lower() in item_nome.lower():
                nome_na_planilha = nome_real
                break

        # Localiza a célula com o nome da conta (ex: procura 'CPFL' na Coluna B)
        try:
            celula = aba.find(nome_na_planilha)
            # Converte valor para formato brasileiro se necessário (vírgula)
            valor_formatado = valor_str.replace('.', ',')

            # Atualiza a coluna ao lado (Coluna C no seu print)
            aba.update_cell(celula.row, celula.col + 1, valor_formatado)
            logger.info(f"✅ Planilha {aba.title} atualizada: {nome_na_planilha} -> R$ {valor_formatado}")
            return True
        except gspread.exceptions.CellNotFound:
            logger.warning(f"⚠️ {nome_na_planilha} não encontrado na aba {aba.title}")
            return False

    except Exception as e:
        logger.error(f"❌ Erro ao acessar Sheets: {e}")
        return False


# --- BLOCO DE TESTE ---
if __name__ == "__main__":
    print("\n🧪 INICIANDO TESTE DE MANIPULAÇÃO DE PLANILHA")
    # Tenta atualizar a CPFL com um valor de teste
    # Certifique-se de que o nome 'CPFL' existe na sua coluna B!
    resultado = atualizar_valor_planilha("CPFL", "250.90")

    if resultado:
        print("🚀 TESTE CONCLUÍDO COM SUCESSO! Verifique seu Google Sheets.")
    else:
        print("verifique se o e-mail da Service Account tem permissão de Editor na planilha.")
