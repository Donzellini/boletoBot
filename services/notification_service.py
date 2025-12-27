import os
import telebot
from telebot import types, apihelper
from core.config import Config
from core.database import get_db_connection
from core.logger import logger
from utils.helpers import formatar_mensagem_boleto

# Configurações iniciais
apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(Config.TELEGRAM_TOKEN)


# --- MIDDLEWARE DE SEGURANÇA ---
@bot.middleware_handler(update_types=['message', 'callback_query'])
def restrict_access(bot_instance, update):
    user_id = update.from_user.id
    if user_id not in Config.ALLOWED_USERS:
        bot.send_message(update.chat.id, "🚫 Acesso Negado.")
        return False


# --- INTERFACE (TECLADO PRINCIPAL) ---
def main_menu():
    # resize_keyboard mantém os botões em um tamanho compacto no celular
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    # Linha 1: Ação Principal (Destaque)
    m.row(types.KeyboardButton("🔍 Buscar Novos Boletos"))

    # Linha 2: Operações Financeiras (Lado a lado)
    m.row(
        types.KeyboardButton("🧾 Boletos Pendentes"),
        types.KeyboardButton("➕ Lançar Gasto")
    )

    # Linha 3: Relatórios e Histórico (Lado a lado)
    m.row(
        types.KeyboardButton("📊 Resumo Mensal"),
        types.KeyboardButton("✅ Ver Pagos")
    )

    # Linha 4: Manutenção (Discreta na base)
    m.row(types.KeyboardButton("🗑️ Limpar Base de Dados"))

    return m


# --- NOTIFICAÇÕES AUTOMÁTICAS ---
def enviar_notificacao_fatura(boleto):
    """Envia a fatura detectada com botão para marcar como pago."""
    mensagem = (
        f"<b>🧾 NOVO BOLETO DETECTADO</b>\n"
        f"📂 <b>Origem:</b> {boleto.origem}\n"
        f"📄 <b>Item:</b> {boleto.titulo}\n"
        f"📄 <b>Mês Referência:</b> {boleto.mes_referencia}\n"
        f"💸 <b>Valor:</b> {boleto.valor if boleto.valor else 'Não identificado'}\n"
    )

    if boleto.pix:
        mensagem += f"\n✨ <b>Pix Copia e Cola:</b>\n<code>{boleto.pix}</code>"
    elif boleto.linha_digitavel:
        mensagem += f"\n🔢 <b>Linha Digitável:</b>\n<code>{boleto.linha_digitavel}</code>"

    # Busca o ID do banco de dados para o botão de callback
    with get_db_connection() as conn:
        res = conn.execute(
            "SELECT id FROM boletos WHERE (pix = ?) OR (linha_digitavel = ?)",
            (boleto.pix, boleto.linha_digitavel)
        ).fetchone()
        id_db = res['id'] if res else "unknown"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Marcar como Pago", callback_data=f"pago_{id_db}"))

    # Envia para todos os usuários permitidos
    for user_id in Config.ALLOWED_USERS:
        try:
            bot.send_message(user_id, mensagem, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erro ao enviar notificação para {user_id}: {e}")


# --- HANDLERS DE COMANDOS ---
@bot.message_handler(commands=['start', 'menu'])
def welcome(message):
    bot.send_message(message.chat.id, "🤖 <b>BoletoBot Central</b>\nGerenciamento financeiro ativo.",
                     reply_markup=main_menu(), parse_mode="HTML")


# --- BUSCA MANUAL ---
@bot.message_handler(func=lambda m: m.text == "🔍 Buscar Novos Boletos")
def trigger_busca_manual(message):
    bot.send_message(message.chat.id, "🔎 Iniciando varredura... Aguarde.")
    try:
        # Import local para evitar Circular Import
        from main import executar_ciclo_coleta
        executar_ciclo_coleta()
        bot.send_message(message.chat.id, "✅ Busca finalizada!")
    except Exception as e:
        logger.error(f"Erro na busca manual: {e}")
        bot.send_message(message.chat.id, "❌ Erro ao realizar busca.")


# --- RESUMO MENSAL ---
@bot.message_handler(func=lambda m: m.text == "📊 Resumo Mensal")
def exibir_resumo(message):
    bot.send_chat_action(message.chat.id, 'typing')
    from services.sheets_service import obter_resumo_financeiro
    resumo = obter_resumo_financeiro()

    if resumo:
        msg = (
            f"📊 <b>RESUMO FINANCEIRO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Total Geral:</b> {resumo['geral']}\n"
            f"👤 <b>Total Baka:</b> {resumo['baka']}\n"
            f"👤 <b>Total Neko:</b> {resumo['neko']}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(message.chat.id, msg, parse_mode="HTML")


# --- RESUMO DE BOLETOS PAGOS ---
@bot.message_handler(func=lambda m: m.text == "✅ Ver Pagos")
def listar_pagos(m):
    with get_db_connection() as conn:
        faturas = conn.execute("SELECT titulo, origem FROM boletos WHERE pago = 1 LIMIT 10").fetchall()

    if not faturas:
        return bot.send_message(m.chat.id, "📭 Nenhum histórico de pagamento.")

    res = "<b>✅ ÚLTIMOS PAGAMENTOS:</b>\n\n"
    res += "\n".join([f"✔️ {f['titulo']} ({f['origem']})" for f in faturas])
    bot.send_message(m.chat.id, res, parse_mode="HTML")


# --- LANÇAMENTO DINÂMICO (FLUXO GUIADO) ---
@bot.message_handler(func=lambda m: m.text == "➕ Lançar Gasto")
def selecionar_categoria(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    botoes = [types.InlineKeyboardButton(cat, callback_data=f"lnc_{cat}") for cat in Config.CATEGORIAS_MANUAIS]
    markup.add(*botoes)
    bot.send_message(message.chat.id, "📁 Selecione a <b>Categoria</b>:", reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith('lnc_'))
def pedir_valor(call):
    categoria = call.data.split('_')[1]
    msg = bot.edit_message_text(f"💰 Categoria: <b>{categoria}</b>\nDigite o <b>Valor</b> (ex: 150,50):",
                                call.message.chat.id, call.message.message_id, parse_mode="HTML")
    bot.register_next_step_handler(msg, processar_valor_manual, categoria)


def processar_valor_manual(message, categoria):
    try:
        valor_limpo = message.text.replace(',', '.')
        valor_float = float(valor_limpo)
        msg = bot.send_message(message.chat.id, f"📝 Valor: R$ {valor_float:.2f}\nDigite a <b>Descrição</b>:")
        bot.register_next_step_handler(msg, finalizar_lancamento_manual, categoria, valor_float)
    except:
        bot.send_message(message.chat.id, "❌ Valor inválido. Tente novamente.")


def finalizar_lancamento_manual(message, categoria, valor):
    from services.sheets_service import lancar_gasto_dinamico
    res = lancar_gasto_dinamico(categoria, message.text, str(valor), message.from_user.id)

    if res["sucesso"]:
        confirmacao = (
            f"✅ <b>Lançado!</b>\n"
            f"📂 {res['categoria']} | 📝 {res['item']}\n"
            f"💰 Total: R$ {res['total']:.2f}\n"
            f"🤝 Parte do {res['nome_parceiro']}: R$ {res['parte_parceiro']:.2f}"
        )
        bot.send_message(message.chat.id, confirmacao, parse_mode="HTML")


# --- GERENCIAMENTO DE BOLETOS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('pago_'))
def confirmar_pagamento(call):
    id_boleto = call.data.split('_')[1]
    with get_db_connection() as conn:
        fatura = conn.execute("SELECT * FROM boletos WHERE id = ?", (id_boleto,)).fetchone()
        conn.execute("UPDATE boletos SET pago = 1 WHERE id = ?", (id_boleto,))

    if fatura:
        from services.sheets_service import atualizar_valor_planilha
        atualizar_valor_planilha(fatura['origem'], fatura['valor'])
        bot.edit_message_text(f"✅ <b>PAGO:</b> {fatura['titulo']}", call.message.chat.id, call.message.message_id,
                              parse_mode="HTML")


@bot.message_handler(func=lambda m: m.text == "🧾 Boletos Pendentes")
def listar_pendentes(m):
    with get_db_connection() as conn:
        faturas = conn.execute("SELECT * FROM boletos WHERE pago = 0").fetchall()

    if not faturas:
        return bot.send_message(m.chat.id, "✅ Nada pendente!")

    for f in faturas:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Marcar como Pago", callback_data=f"pago_{f['id']}"))
        msg_formatada = formatar_mensagem_boleto(f)
        bot.send_message(
            m.chat.id,
            msg_formatada,
            reply_markup=markup,
            parse_mode="Markdown"
        )


# --- LIMPEZA DA BASE ---
@bot.message_handler(func=lambda m: m.text == "🗑️ Limpar Base de Dados")
def confirmar_limpeza(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚠️ SIM, APAGAR TUDO", callback_data="confirmar_reset_db"))
    markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_operacao"))

    bot.send_message(
        message.chat.id,
        "❓ <b>Tem certeza?</b>\nIsto apagará todos os boletos identificados (pendentes e pagos) e não pode ser desfeito.",
        reply_markup=markup,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data == "confirmar_reset_db")
def resetar_db(call):
    from core.database import get_db_connection
    try:
        with get_db_connection() as conn:
            # Apaga os dados mas mantém a estrutura das tabelas
            conn.execute("DELETE FROM boletos")
            # Reinicia o contador de IDs (opcional)
            conn.execute("DELETE FROM sqlite_sequence WHERE name='boletos'")
            conn.commit()

        bot.edit_message_text("✅ <b>Base de dados limpa com sucesso!</b>",
                              call.message.chat.id, call.message.message_id, parse_mode="HTML")
        logger.info("🗑️ Base de dados resetada pelo usuário.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Erro ao limpar base: {e}")


@bot.callback_query_handler(func=lambda call: call.data == "cancelar_operacao")
def cancelar_acao(call):
    bot.edit_message_text("❌ Operação cancelada.", call.message.chat.id, call.message.message_id)

