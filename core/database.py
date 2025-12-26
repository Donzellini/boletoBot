import sqlite3
import os
from core.config import Config

# Define o caminho do banco de dados baseado no diretório temporário configurado
DB_PATH = os.path.join(os.path.dirname(Config.TEMP_DIR), "boletos.db")


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
                         id
                         INTEGER
                         PRIMARY
                         KEY
                         AUTOINCREMENT,
                         origem
                         TEXT,
                         titulo
                         TEXT,
                         linha_digitavel
                         TEXT,
                         pix
                         TEXT,
                         valor
                         TEXT, -- Armazenado como TEXT para preservar a formatação original
                         pago
                         INTEGER
                         DEFAULT
                         0,
                         data_identificacao
                         TIMESTAMP
                         DEFAULT
                         CURRENT_TIMESTAMP
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
            "(linha_digitavel IS NOT NULL AND linha_digitavel = ?)",
            (boleto.pix, boleto.linha_digitavel)
        ).fetchone()

        if not existe:
            conn.execute(
                "INSERT INTO boletos (origem, titulo, linha_digitavel, pix, valor) "
                "VALUES (?, ?, ?, ?, ?)",
                (boleto.origem, boleto.titulo, boleto.linha_digitavel, boleto.pix, boleto.valor)
            )
            conn.commit()
            return True

        return False