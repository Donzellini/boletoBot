# 🤖 BoletoBot

O **BoletoBot** é um assistente inteligente no Telegram projetado para automatizar o controle financeiro doméstico. Ele realiza a varredura de e-mails e portais de serviços, extrai códigos de barras ou PIX e lança os valores diretamente em uma planilha do Google Sheets.

---

## 🛠️ Como Rodar o Projeto (Desenvolvedor)

### 1. Pré-requisitos

* **Python 3.12**
* **Google Cloud Console**: Habilitar a API do Google Sheets e Drive para obter o `credentials.json`.
* **Anti-Captcha**: Chave de API para resolução de Captchas (necessário para o portal SEMAE).
* **Fly.io CLI**: (Opcional) Para realizar o deploy em nuvem com suporte a **Swap** e volumes persistentes.

### 2. Configuração de Ambiente

Crie um arquivo `.env` na raiz do projeto seguindo o modelo `env.example`:

```env
GMAIL_USER=seu_email@gmail.com
GMAIL_APP_PASSWORD=sua_senha_app_google
LABELS_INTERESSE=Finances/Aluguel,Finances/CPFL,Finances/Claro,Finances/Comgás
CPF_SENHA=seu_cpf_para_pdfs_protegidos
ANTICAPTCHA_KEY=sua_chave_anticaptcha
TELEGRAM_TOKEN=token_do_seu_bot
ALLOWED_USERS=id_telegram_1,id_telegram_2
ID_NEKO=id_identificacao_rateio_1
ID_BAKA=id_identificacao_rateio_2
SHEET_NAME=Nome da Sua Planilha no Drive
MAPA_CATEGORIAS=Finances/CPFL:CPFL,Finances/Comgás:COMGÁS

```

### 3. Instalação e Execução

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar o bot localmente
python main.py

```

---

## 📱 Guia de Uso (Usuário Final)

Ao iniciar o bot com o comando `/start`, o painel principal será exibido com as seguintes opções:

### 🔍 Buscar Novos Boletos

* **O que faz**: O bot entra no Gmail e nos portais (LLZ, SEMAE) em busca de contas pendentes.
* **Inteligência de Data**: Ele lê o conteúdo do boleto para identificar o **Mês de Referência** (competência), garantindo que uma conta de Janeiro que chegou em Dezembro seja registrada corretamente.
* **Notificação**: Se você solicitou a busca manualmente, os cards de novos boletos serão enviados **apenas para você**.

### 🧾 Boletos Pendentes

* Exibe a lista de faturas encontradas que ainda não foram pagas.
* Cada card possui o botão **✅ Marcar como Pago**. Ao clicar:
1. O bot atualiza o status no banco de dados.
2. O valor é lançado automaticamente na aba correta (MM/AAAA) da sua planilha.



### ➕ Lançar Gasto

* Permite registrar gastos manuais (Mercado, Lazer, etc) diretamente pelo chat.
* **Fluxo**: Escolha a Categoria ➔ Digite o Valor ➔ Digite a Descrição ➔ Confirme o Mês (MM/AAAA).
* **Regra da Fiança**: Lançamentos na categoria `CASA` com o nome `FIANÇA` atualizam a linha existente em vez de criar uma nova, evitando duplicidade.

### 📊 Resumo Mensal

* Consulta os totais acumulados da planilha do Google Sheets para o mês atual, mostrando os saldos individuais.

### 🗑️ Limpar Base de Dados

* Apaga o histórico local de boletos identificados. Útil para testes ou limpeza de dados antigos. Requer confirmação via menu.

---

## 🚀 Notas de Deploy (Fly.io)

O projeto utiliza um `Dockerfile` otimizado para ambientes de baixa memória:

* **Swap Automatizado**: Cria 512MB de memória virtual no boot para suportar o Chrome Headless sem travamentos.
* **Persistência**: O banco de dados SQLite é armazenado no volume `/data`, preservando os dados entre reinicializações.

## TODO

- [ ] Rever data de competência da conta de água 
  - Recupera o mês de competência, e não a data de vencimento, então lança na aba incorreta da planilha.
- [ ] Rever lógica de busca dos boletos do endereço eletrónico
  - Possível ajuste: buscar o mês passado inteiro e o atual
  - Melhorar a identificação do mês de competência
- [ ] Feature: acrescentar no resumo o detalhamento das despesas
- [ ] Feature: Melhorar a descrição dos bletos pagos