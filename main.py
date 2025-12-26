import os
from coletor_gmail import processar_email
from scrapers import scrap_semae_piracicaba, scrap_llz_condominio
from parser_pdf import extrair_dados_pdf
import glob


def executar_automacao():
    print("🚀 Iniciando Ciclo de Automação de Boletos")

    # 1. Coleta do Gmail (O que já está funcionando)
    boletos_gmail = processar_email()

    # 2. Executa Scrapers Web (SEMAE / LLZ)
    # Eles vão salvar arquivos em /tmp/boleto_bot
    #scrap_semae_piracicaba()
    #scrap_llz_condominio()

    # 3. Processa todos os PDFs que caíram na pasta temp
    print("\n🧐 Processando arquivos baixados pelos scrapers...")
    arquivos_baixados = glob.glob("/tmp/boleto_bot/*.pdf")

    for pdf in arquivos_baixados:
        # Lógica para decidir se precisa de senha (ex: se o nome tiver 'Comgas')
        senha = os.getenv("CPF_SENHA") if "comgás" in pdf.lower() else None
        codigo = extrair_dados_pdf(pdf, password=senha)
        print(f"📄 Arquivo: {os.path.basename(pdf)} | Código: {codigo}")


if __name__ == "__main__":
    executar_automacao()
