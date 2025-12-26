import os
import telebot
from telebot import types, apihelper
from core.config import Config
from core.database import get_db_connection
from utils.helpers import logger

apihelper.ENABLE_MIDDLEWARE = True

# Inicializa o bot com o Token do Config
bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN", ""))
ALLOWED_USERS = [int(u.strip()) for u in os.getenv("ALLOWED_USERS", "").split(",") if u.strip()]


# --- MIDDLEWARE DE SEGURANÇA ---
@bot.middleware_handler(update_types=['message', 'callback_query'])
def restrict_access(bot_instance, update):
    user_id = update.from_user.id
    if user_id not in ALLOWED_USERS:
        bot.send_message(update.chat.id, "🚫 Acesso Negado.")
        return False


# --- INTERFACE ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(types.KeyboardButton("🔍 Buscar Novos Boletos"))
    m.add(types.KeyboardButton("📊 Resumo Mensal"))
    m.add(types.KeyboardButton("🧾 Boletos Pendentes"), types.KeyboardButton("➕ Lançar Gasto"))
    m.add(types.KeyboardButton("✅ Ver Pagos"))
    return m


def enviar_notificacao_fatura(boleto):
    """Envia a fatura com o botão de marcação correto usando o ID do Banco."""
    mensagem = (
        f"<b>🧾 NOVO BOLETO DETECTADO</b>\n"
        f"📂 <b>Origem:</b> {boleto.origem}\n"
        f"📄 <b>Item:</b> {boleto.titulo}\n\n"
        f"💸 <b>Valor:</b> {boleto.valor if boleto.valor else 'Não identificado'}\n\n"
    )

    if boleto.pix:
        mensagem += f"✨ <b>Pix Copia e Cola:</b>\n<code>{boleto.pix}</code>"
    elif boleto.linha_digitavel:
        mensagem += f"🔢 <b>Linha Digitável:</b>\n<code>{boleto.linha_digitavel}</code>"

    # Busca o ID real gerado pelo SQLite para este boleto
    with get_db_connection() as conn:
        res = conn.execute(
            "SELECT id FROM boletos WHERE (pix IS NOT NULL AND pix = ?) OR (linha_digitavel IS NOT NULL AND linha_digitavel = ?)",
            (boleto.pix, boleto.linha_digitavel)
        ).fetchone()
        id_db = res['id'] if res else "desconhecido"

    # CRIAÇÃO DO BOTÃO (Apenas uma vez, usando o id_db)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Marcar como Pago", callback_data=f"pago_{id_db}"))


# --- HANDLERS ---
@bot.message_handler(commands=['start', 'menu'])
def welcome(message):
    bot.send_message(message.chat.id, "🤖 <b>BoletoBot Central</b>\n\nFaturas automáticas e gestão de pagamentos.",
                     reply_markup=main_menu(), parse_mode="HTML")


@bot.message_handler(func=lambda m: m.text == "🧾 Boletos Pendentes")
def listar_pendentes(m):
    with get_db_connection() as conn:
        faturas = conn.execute("SELECT * FROM boletos WHERE pago = 0").fetchall()

    if not faturas:
        return bot.send_message(m.chat.id, "✅ Nenhuma fatura pendente!")

    for f in faturas:
        msg = (f"<b>🧾 {f['titulo']}</b>\n"
               f"📂 {f['origem']}\n"
               f"💸 {f['valor']}\n")
        if f['pix']:
            msg += f"<code>{f['pix']}</code>"
        elif f['linha_digitavel']:
            msg += f"<code>{f['linha_digitavel']}</code>"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Marcar como Pago", callback_data=f"pago_{f['id']}"))
        bot.send_message(m.chat.id, msg, reply_markup=markup, parse_mode="HTML")


@bot.message_handler(func=lambda m: m.text == "✅ Ver Pagos")
def listar_pagos(m):
    with get_db_connection() as conn:
        faturas = conn.execute("SELECT titulo, origem FROM boletos WHERE pago = 1 LIMIT 10").fetchall()

    if not faturas:
        return bot.send_message(m.chat.id, "📭 Nenhum histórico de pagamento.")

    res = "<b>✅ ÚLTIMOS PAGAMENTOS:</b>\n\n"
    res += "\n".join([f"✔️ {f['titulo']} ({f['origem']})" for f in faturas])
    bot.send_message(m.chat.id, res, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith('pago_'))
def confirmar_pagamento(call):
    # 1. RESPONDA IMEDIATAMENTE ao Telegram para evitar o timeout
    try:
        bot.answer_callback_query(call.id, "Processando pagamento...")
    except:
        pass  # Ignora se já tiver expirado

    id_boleto = call.data.split('_')[1]

    # 2. Atualiza o banco de dados
    with get_db_connection() as conn:
        fatura = conn.execute("SELECT * FROM boletos WHERE id = ?", (id_boleto,)).fetchone()
        conn.execute("UPDATE boletos SET pago = 1 WHERE id = ?", (id_boleto,))
        conn.commit()

    # 3. Processa a planilha (agora o Telegram não vai mais reclamar do tempo)
    if fatura:
        from services.sheets_service import atualizar_valor_planilha
        atualizar_valor_planilha(fatura['origem'], fatura['valor'])

    # 4. Atualiza o visual da mensagem
    texto_atual = call.message.text
    novo_texto = f"✅ <b>PAGO E ARQUIVADO</b>\n\n<s>{texto_atual}</s>"

    try:
        bot.edit_message_text(
            novo_texto,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Erro ao editar: {e}")

# --- BUSCA MANUAL DE BOLETOS ---

@bot.message_handler(func=lambda m: m.text == "🔍 Buscar Novos Boletos")
def trigger_busca_manual(message):
    bot.send_message(message.chat.id, "🔎 Iniciando varredura no Gmail e Portais... Aguarde.")
    try:
        from main import executar_ciclo_coleta
        executar_ciclo_coleta()
        bot.send_message(message.chat.id, "✅ Busca finalizada!")
    except Exception as e:
        logger.error(f"Erro na busca manual: {e}")
        bot.send_message(message.chat.id, "❌ Erro ao realizar busca.")


@bot.message_handler(func=lambda m: m.text == "➕ Lançar Gasto")
def selecionar_categoria(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Pega as categorias da sua ENV para gerar os botões automaticamente
    categorias = os.getenv("CATEGORIAS_MANUAIS", "Lazer,Mercado,Carro,Meninas").split(',')

    botoes = [types.InlineKeyboardButton(cat.strip(), callback_data=f"lnc_{cat.strip()}") for cat in categorias]
    markup.add(*botoes)

    bot.send_message(message.chat.id, "📁 Selecione a **Categoria** do gasto:", reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith('lnc_'))
def pedir_valor(call):
    categoria = call.data.split('_')[1]
    msg = bot.edit_message_text(f"💰 Categoria: **{categoria}**\n\nDigite o **Valor** (ex: 150.50):",
                                call.message.chat.id, call.message.message_id, parse_mode="HTML")

    # Registra que o próximo passo será ler o valor
    bot.register_next_step_handler(msg, processar_valor_manual, categoria)


def processar_valor_manual(message, categoria):
    valor_texto = message.text.replace(',', '.')
    try:
        valor_float = float(valor_texto)
        msg = bot.send_message(message.chat.id,
                               f"📝 Valor: R$ {valor_float:.2f}\nAgora digite uma **Descrição** (ou 'pular'):")
        bot.register_next_step_handler(msg, finalizar_lancamento_manual, categoria, valor_float)
    except ValueError:
        bot.send_message(message.chat.id,
                         "❌ Valor inválido! Use apenas números e ponto. Tente novamente clicando em 'Lançar Gasto'.")


def finalizar_lancamento_manual(message, categoria, valor):
    descricao = message.text if message.text.lower() != 'pular' else categoria

    from services.sheets_service import lancar_gasto_dinamico

    # Passamos o message.from_user.id para saber quem enviou
    resultado = lancar_gasto_dinamico(categoria, descricao, str(valor), message.from_user.id)

    if resultado["sucesso"]:
        res = (
            f"✅ <b>Lançado com Sucesso!</b>\n\n"
            f"📂 <b>Categoria:</b> {resultado['categoria']}\n"
            f"📝 <b>Item:</b> {resultado['item']}\n"
            f"💰 <b>Total:</b> R$ {resultado['total']:.2f}\n"
            f"🤝 <b>Parte do {resultado['nome_parceiro']}:</b> R$ {resultado['parte_parceiro']:.2f}"
        )
        bot.send_message(message.chat.id, res, reply_markup=main_menu(), parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "💥 Erro ao salvar na planilha.")


@bot.message_handler(func=lambda m: m.text == "📊 Resumo Mensal")
def exibir_resumo(message):
    bot.send_chat_action(message.chat.id, 'typing')

    from services.sheets_service import obter_resumo_financeiro

    resumo = obter_resumo_financeiro()

    if resumo:
        # Monta a mensagem baseada nos dados da sua Tabela 5 (H11, H12, H13)
        msg = (
            f"📊 <b>RESUMO FINANCEIRO DO MÊS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Total Geral:</b> {resumo['geral']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Total Neko:</b> {resumo['neko']}\n"
            f"👤 <b>Total Baka:</b> {resumo['baka']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Valores atualizados conforme a planilha.</i>"
        )
        bot.send_message(message.chat.id, msg, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "❌ Não foi possível ler os dados da planilha.")