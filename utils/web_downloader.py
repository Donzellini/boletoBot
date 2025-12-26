import requests
import os
from core.config import Config
from core.logger import logger


def baixar_boleto_bevi(url_bevi):
    """
    Realiza o download de boletos a partir de URLs externas.
    Utilizado principalmente para faturas de aluguel (Bevi/Superlógica).
    """
    file_path = os.path.join(Config.TEMP_DIR, "Aluguel_Bevi_Download.pdf")

    # Headers para mimetizar um navegador comum e evitar bloqueios
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        logger.info(f"📡 Solicitando download via link externo: {url_bevi}")

        # Faz a requisição com timeout para não travar o bot
        response = requests.get(url_bevi, headers=headers, timeout=20, allow_redirects=True)

        # Verifica se a requisição foi bem-sucedida e se o conteúdo é um PDF
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()

            if 'application/pdf' in content_type or url_bevi.lower().endswith('.pdf'):
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"✅ Download concluído: {file_path}")
                return file_path
            else:
                logger.warning(f"⚠️ O link não retornou um PDF válido (Content-Type: {content_type})")
        else:
            logger.error(f"❌ Falha no download. Status Code: {response.status_code}")

    except Exception as e:
        logger.error(f"❌ Erro durante o download do boleto externo: {e}")

    return None