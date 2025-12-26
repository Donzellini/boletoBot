import requests
import os
from core.config import Config


def baixar_boleto_bevi(url_bevi):
    file_path = os.path.join(Config.TEMP_DIR, "Finances_Aluguel_Bevi_Download.pdf")
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        print(f"  📡 Baixando boleto via link externo...")
        response = requests.get(url_bevi, headers=headers, timeout=15)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', '').lower():
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path
    except Exception as e:
        print(f"  ❌ Erro no download: {e}")
    return None
