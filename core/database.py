import sqlite3
import os
from core.config import Config

DB_PATH = os.path.join(os.path.dirname(Config.TEMP_DIR), "boletos.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
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
    """Salva apenas se o boleto (pela linha ou pix) não existir."""
    with get_db_connection() as conn:
        # Evita duplicatas
        existe = conn.execute(
            "SELECT id FROM boletos WHERE (pix IS NOT NULL AND pix = ?) OR (linha_digitavel IS NOT NULL AND linha_digitavel = ?)",
            (boleto.pix, boleto.linha_digitavel)
        ).fetchone()

        if not existe:
            conn.execute(
                "INSERT INTO boletos (origem, titulo, linha_digitavel, pix) VALUES (?, ?, ?, ?)",
                (boleto.origem, boleto.titulo, boleto.linha_digitavel, boleto.pix)
            )
            conn.commit()
            return True
        else:
            return False