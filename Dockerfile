FROM python:3.12-slim

# Instalar dependências do sistema para o Selenium e Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código do bot
COPY . .

# Criar pasta temporária para os PDFs conforme configurado no Config
RUN mkdir -p /tmp/boleto_bot

# Comando para rodar o bot
CMD ["python", "main.py"]