import os
import re
from datetime import datetime

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
        types.KeyboardButton("🧾 Detalhes do Mês")
    )

    m.row(
        types.KeyboardButton("✅ Ver Pagos"),
        types.KeyboardButton("🗑️ Limpar Base de Dados")
    )

    return m


# --- NOTIFICAÇÕES AUTOMÁTICAS ---
def enviar_notificacao_fatura(boleto, target_user=None):
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
    markup.add(types.InlineKeyboardButton("📊 Lançar na Planilha", callback_data=f"lncsht_{id_db}"))
    markup.add(types.InlineKeyboardButton("✅ Marcar como Pago", callback_data=f"pago_{id_db}"))

    destinatarios = [target_user] if target_user else Config.ALLOWED_USERS
    for user_id in destinatarios:
        try:
            bot.send_message(user_id, mensagem, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erro ao enviar notificação para {user_id}: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('lncsht_'))
def processar_lancamento_planilha(call):
    bot.answer_callback_query(call.id, "⌛ Processando lançamento...")
    id_boleto = call.data.split('_')[1]

    with get_db_connection() as conn:
        fatura = conn.execute("SELECT * FROM boletos WHERE id = ?", (id_boleto,)).fetchone()

    if fatura:
        from services.sheets_service import atualizar_valor_planilha
        sucesso = atualizar_valor_planilha(fatura['origem'], fatura['valor'], fatura['mes_referencia'])

        if sucesso:
            novo_texto = call.message.text + "\n\n✅ <b>Provisionado na planilha!</b>"
            bot.edit_message_text(novo_texto, call.message.chat.id, call.message.message_id,
                                  reply_markup=call.message.reply_markup, parse_mode="HTML")
        else:
            bot.send_message(call.message.chat.id, "❌ Erro ao atualizar planilha da Comgás.")


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
        executar_ciclo_coleta(solicitante_id=message.from_user.id)
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
    """Agora, em vez de salvar direto, pergunta o mês."""
    descricao = message.text
    # Sugere o mês atual como padrão para facilitar
    mes_atual = datetime.now().strftime("%m/%Y")

    msg = bot.send_message(
        message.chat.id,
        f"📅 Para qual <b>mês</b> é esse gasto?\nResponda no formato MM/AAAA (Ex: {mes_atual}):"
    )
    # Passa os dados acumulados para o passo final
    bot.register_next_step_handler(msg, salvar_final_com_mes, categoria, valor, descricao)


def salvar_final_com_mes(message, categoria, valor, descricao):
    """Recebe o mês e finalmente envia para a planilha."""
    mes_ref = message.text.strip()

    # Validação simples de formato
    if not re.match(r'\d{2}/\d{4}', mes_ref):
        bot.send_message(message.chat.id, "❌ Formato inválido! Use MM/AAAA. Tente lançar novamente.")
        return

    from services.sheets_service import lancar_gasto_dinamico
    # Enviamos o mes_ref para o serviço de planilha
    res = lancar_gasto_dinamico(categoria, descricao, str(valor), message.from_user.id, mes_referencia=mes_ref)

    if res["sucesso"]:
        confirmacao = (
            f"✅ <b>Lançado em {mes_ref}!</b>\n"
            f"📂 {res['categoria']} | 📝 {res['item']}\n"
            f"💰 Total: R$ {res['total']:.2f}"
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
        atualizar_valor_planilha(fatura['origem'], fatura['valor'], fatura['mes_referencia'])
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
        markup.add(types.InlineKeyboardButton("📊 Lançar na Planilha", callback_data=f"lncsht_{f['id']}"))
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


@bot.message_handler(func=lambda m: m.text == "🧾 Detalhes do Mês")
def selecionar_mes_detalhes(message):
    """Primeiro passo: Selecionar qual mês deseja visualizar."""
    markup = types.InlineKeyboardMarkup(row_width=3)

    # Gerar botões para os últimos 6 meses (exemplo)
    from datetime import datetime, timedelta

    hoje = datetime.now().replace(day=15)
    botoes = []

    for i in range(-3, 4):
        # Lógica para calcular o mês relativo
        data_alvo = hoje + timedelta(days=i * 30)
        mes_ano = data_alvo.strftime("%m/%Y")

        # Um diferencial visual: colocar um ícone no mês atual
        label = f"📍 {mes_ano}" if i == 0 else mes_ano

        botoes.append(types.InlineKeyboardButton(
            label,
            callback_data=f"detalhe_mes_{mes_ano}"
        ))

    markup.add(*botoes)
    bot.send_message(message.chat.id, "📅 Selecione o <b>mês</b> para ver os detalhes:",
                     reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith('detalhe_mes_'))
def processar_detalhes_por_mes(call):
    """Segundo passo: Buscar dados da aba selecionada."""
    mes_selecionado = call.data.split('_')[-1]
    bot.answer_callback_query(call.id, f"⌛ Buscando dados de {mes_selecionado}...")

    from services.sheets_service import obter_gastos_detalhados
    gastos = obter_gastos_detalhados(mes_alvo=mes_selecionado)  # Passamos o mês escolhido

    if not gastos:
        return bot.send_message(call.message.chat.id, f"📭 Nenhuma informação em <b>{mes_selecionado}</b>.",
                                parse_mode="HTML")

    msg = f"📝 <b>LISTA DETALHADA - {mes_selecionado}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    for g in gastos:
        emoji_n = "🟢" if "-" in str(g['neko']) else "🔴"
        emoji_b = "🟢" if "-" in str(g['baka']) else "🔴"

        linha = (
            f"🔹 <b>{g['item']}</b> ({g['categoria']})\n"
            f"💰 Total: <code>R$ {g['valor']}</code>\n"
            f"└ 🙋‍♂️ Neko: {emoji_n} <code>{g['neko']}</code> | 🙋‍♀️ Baka: {emoji_b} <code>{g['baka']}</code>\n"
            "────────────────────\n"
        )

        if len(msg + linha) > 4000:
            bot.send_message(call.message.chat.id, msg, parse_mode="HTML")
            msg = ""
        msg += linha

    bot.send_message(call.message.chat.id, msg, parse_mode="HTML")
