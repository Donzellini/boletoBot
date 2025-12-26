def exibir_resultado(res):
    print(f"📧 {res['assunto']}")
    if res['pix']: print(f"  ✨ PIX: {res['pix'][:30]}...")
    if res['linha_digitavel']: print(f"  🔢 Linha: {res['linha_digitavel']}")
    if res['link_bevi']: print(f"  🔗 Link Bevi: {res['link_bevi']}")
    if not any([res['pix'], res['linha_digitavel'], res['link_bevi']]):
        print("  ⚠️ Nada encontrado.")
