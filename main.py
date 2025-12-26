import services.scrapers as scrapers_module
from core.config import Config
from services.gmail_service import buscar_faturas_email
from utils.helpers import exibir_resultado


def executar_automacao():
    print("🚀 BOLETO BOT: Execução Dinâmica via Reflecção\n")

    # 1. Processar Gmail
    lista_final = buscar_faturas_email()

    # 2. Executar Scrapers chamando a função pelo nome (string)
    print(f"🌐 Verificando funções no .env: {Config.LISTA_FUNCOES_SCRAPERS}")

    for nome_funcao in Config.LISTA_FUNCOES_SCRAPERS:
        try:
            # Tenta encontrar a função dentro do módulo scrapers.py
            funcao_para_rodar = getattr(scrapers_module, nome_funcao, None)

            if funcao_para_rodar and callable(funcao_para_rodar):
                print(f"🔎 Rodando função: {nome_funcao}")
                resultado = funcao_para_rodar()
                if resultado:
                    lista_final.append(resultado)
            else:
                print(f"⚠️ Erro: A função '{nome_funcao}' não existe em services/scrapers.py")

        except Exception as e:
            print(f"❌ Falha crítica ao executar {nome_funcao}: {e}")

    # 3. Resultado Final
    print(f"\n📊 Processamento concluído: {len(lista_final)} faturas.")
    for fatura in lista_final:
        exibir_resultado(fatura)


if __name__ == "__main__":
    executar_automacao()