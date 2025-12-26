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
    m.add(types.KeyboardButton("🧾 Boletos Pendentes"), types.KeyboardButton("✅ Ver Pagos"))
    return m


def enviar_notificacao_fatura(boleto):
    """Envia a fatura com o botão de marcação."""
    mensagem = (
        f"<b>🧾 NOVO BOLETO DETECTADO</b>\n"
        f"📂 <b>Origem:</b> {boleto.origem}\n"
        f"📄 <b>Item:</b> {boleto.titulo}\n\n"
        f"💸 <b>Valor:</b> {boleto.valor}\n\n"
    )

    if boleto.pix:
        mensagem += f"✨ <b>Pix Copia e Cola:</b>\n<code>{boleto.pix}</code>"
    elif boleto.linha_digitavel:
        mensagem += f"🔢 <b>Linha Digitável:</b>\n<code>{boleto.linha_digitavel}</code>"

    with get_db_connection() as conn:
        res = conn.execute(
            "SELECT id FROM boletos WHERE (pix IS NOT NULL AND pix = ?) OR (linha_digitavel IS NOT NULL AND linha_digitavel = ?)",
            (boleto.pix, boleto.linha_digitavel)
        ).fetchone()
        id_db = res['id'] if res else "desconhecido"

    markup = types.InlineKeyboardMarkup()
    # AGORA o callback_data será 'pago_123' em vez de 'pago_Título'
    markup.add(types.InlineKeyboardButton("✅ Marcar como Pago", callback_data=f"pago_{id_db}"))

    markup = types.InlineKeyboardMarkup()
    # Guardamos o título resumido no callback
    markup.add(types.InlineKeyboardButton("✅ Marcar como Pago", callback_data=f"pago_{boleto.titulo[:15]}"))

    for user_id in ALLOWED_USERS:
        bot.send_message(user_id, mensagem, reply_markup=markup, parse_mode="HTML")


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
        msg = f"<b>🧾 {f['titulo']}</b>\n📂 {f['origem']}\n"
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
    id_boleto = call.data.split('_')[1]

    # 1. Atualiza o status no Banco de Dados
    with get_db_connection() as conn:
        fatura = conn.execute("SELECT * FROM boletos WHERE id = ?", (id_boleto,)).fetchone()
        conn.execute("UPDATE boletos SET pago = 1 WHERE id = ?", (id_boleto,))
        conn.commit()

    if fatura:
        # Envia para o Sheets (converte o nome para o que está na planilha se necessário)
        from services.sheets_service import atualizar_valor_planilha
        atualizar_valor_planilha(fatura['origem'], fatura['valor'])

    # 2. Recupera o texto atual da mensagem para riscar
    texto_atual = call.message.text

    # Adicionamos o Check verde e risca o texto original
    novo_texto = f"✅ <b>PAGO E ARQUIVADO</b>\n\n<s>{texto_atual}</s>"

    try:
        # Editamos a mensagem removendo os botões (markup=None) e riscando o texto
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=novo_texto,
            parse_mode="HTML",
            reply_markup=None  # Remove o botão após clicar
        )
        bot.answer_callback_query(call.id, "Pagamento registrado!")
        logger.info(f"✅ Boleto ID {id_boleto} marcado como pago no Telegram.")
    except Exception as e:
        logger.error(f"❌ Erro ao riscar mensagem no Telegram: {e}")
        bot.answer_callback_query(call.id, "Erro ao atualizar visualmente.")
