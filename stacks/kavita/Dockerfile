FROM golang:1.21-alpine

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    bash \
    gnupg \
    software-properties-common \
    python3 \
    python3-pip \
    wget \
    git \
    build-essential \
    libmupdf-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Compiler cbconvert depuis les sources avec la bonne commande
RUN CGO_ENABLED=1 go install github.com/gen2brain/cbconvert/cmd/cbconvert@latest

# Installation de F2 via Go (dernière version)
RUN go install github.com/ayoisaiah/f2/v2/cmd/f2@latest

# Ajout du PATH Go
ENV PATH="/root/go/bin:${PATH}"

# Création des répertoires de travail
WORKDIR /app
COPY kavita_script.py /app/

# Création d'un script wrapper
RUN echo '#!/bin/bash\n\
python3 /app/kavita_script.py\n' > /app/entrypoint.sh && \
chmod +x /app/entrypoint.sh

# Création du point de montage pour les volumes
VOLUME ["/mnt/storage/kavita"]

# Exécution du script
ENTRYPOINT ["/app/entrypoint.sh"]