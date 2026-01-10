FROM python:3.12-slim-bullseye

# Instala Chromium e dependências
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Criar script de inicialização para forçar o swap
RUN echo '#!/bin/sh \n\
# Ativação do Swap (essencial para Fly.io low memory) \n\
fallocate -l 512M /swapfile || true \n\
chmod 600 /swapfile || true \n\
mkswap /swapfile || true \n\
swapon /swapfile || true \n\
\n\
# LOOP INFINITO: Mesmo que o Python morra, o bash não sai. \n\
while true; do \n\
    python main.py \n\
    echo "Processo Python finalizado com código $?. Reiniciando em 10s..." \n\
    sleep 10 \n\
done' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# O container agora roda o script de boot
CMD ["/app/entrypoint.sh"]