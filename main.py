from services.gmail_service import buscar_faturas_email
from services.scrapers import scrap_llz_condominio, scrap_semae_piracicaba
from utils.helpers import exibir_resultado

def executar_automacao():
    print("🚀 BOLETO BOT: Iniciando Ciclo de Orquestração\n")

    # 1. Processar Gmail
    lista_faturas = buscar_faturas_email()

    # 2. Processar Scrapers (Pode retornar um Boleto ou None)
    boleto_llz = scrap_llz_condominio()
    if boleto_llz: lista_faturas.append(boleto_llz)

    # 3. Exibir Resumo e futuramente enviar para Telegram
    print(f"\n📊 Resumo da Coleta: {len(lista_faturas)} itens encontrados.")
    for fatura in lista_faturas:
        exibir_resultado(fatura)

if __name__ == "__main__":
    executar_automacao()