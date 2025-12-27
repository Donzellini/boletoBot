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
- [ ] Botão de limpeza da base de boletos, para facilitar testes
- [ ] Implementar leitura da conta de água (temos somente o ‘login’, não há boletos disponíveis)
- [ ] Ajustar visual dos botões
- [ ] Recuperar valor do boleto do condominio
- [ ] Recuperar data dos boletos e validar no banco se o boleto daqela conta e daquele mes já foram lançados