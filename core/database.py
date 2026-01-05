import sqlite3
import os

if os.path.exists("/data"):
    DB_PATH = "/data/boletos.db"
else:
    DB_PATH = os.path.join(os.getcwd(), "boletos.db")


def get_db_connection():
    """Estabelece conexão com o SQLite e configura o retorno como dicionário."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    """Cria a tabela de boletos caso ela ainda não exista."""
    with get_db_connection() as conn:
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS boletos
                     (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         origem TEXT,
                         titulo TEXT,
                         linha_digitavel TEXT,
                         pix TEXT,
                         valor TEXT,
                         pago INTEGER DEFAULT 0,
                         mes_referencia TEXT,
                         data_identificacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                     )
                     """)
        conn.commit()


def salvar_boleto_db(boleto):
    """
    Salva o boleto no banco apenas se ele for inédito.
    Verifica duplicidade pela Linha Digitável ou pelo PIX.
    """
    with get_db_connection() as conn:
        # Busca por duplicatas existentes
        existe = conn.execute(
            "SELECT id FROM boletos WHERE "
            "(pix IS NOT NULL AND pix = ?) OR "
            "(linha_digitavel IS NOT NULL AND linha_digitavel = ?) OR"
            "(origem = ? AND mes_referencia = ?)",
            (boleto.pix, boleto.linha_digitavel, boleto.origem, boleto.mes_referencia)
        ).fetchone()
        # existe = False

        if not existe:
            conn.execute(
                "INSERT INTO boletos (origem, titulo, linha_digitavel, pix, valor, mes_referencia) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (boleto.origem, boleto.titulo, boleto.linha_digitavel, boleto.pix, boleto.valor, boleto.mes_referencia)
            )
            conn.commit()
            return True

        return False