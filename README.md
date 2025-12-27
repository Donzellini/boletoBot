# 🤖 Boleto Bot (Piracicaba Edition)

Automação inteligente para coleta de faturas e extração de códigos de barras/PIX.

## 🛠️ Funcionalidades
- **Gmail:** Varredura de labels específicas para CPFL, Claro e Comgás.
- **Scrapers Web:** Login automático e quebra de CAPTCHA (reCAPTCHA v2) para SEMAE e LLZ.
- **Bevi:** Download automático de boletos via links da Superlógica.
- **Parser:** Extração de linha digitável de PDFs (com e sem senha).

## 🚀 Tecnologias
- Python 3.12
- Selenium & Webdriver Manager
- Imap-tools (IMAP)
- Pdfplumber
- Anti-Captcha API

## TO-DO
- [x] Botão de limpeza da base de boletos, para facilitar testes
- [ ] Implementar leitura da conta de água (temos somente o ‘login’, não há boletos disponíveis)
- [x] Ajustar visual dos botões
- [x] Recuperar valor do boleto do condominio
- [x] Recuperar data dos boletos e validar no banco se o boleto daquela conta e daquele mes já foram lançados
  - [ ] Recuperou a data do email, o ideal é recuperar do próprio boleto