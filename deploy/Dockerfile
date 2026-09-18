# Imagen de la API + web de QReaper para el VPS.
#
#   - No publica puertos: la única puerta es Traefik (stack de /opt/bdev).
#   - Se engancha a la red externa `bdev_default` para que Traefik lo vea.
#   - Sandbox LOCAL (Chromium headless): QREAPER_SANDBOX=local.
#   - La BD SQLite persiste en el volumen `qreaper-data`.
#
# Uso:
#   cd /opt/qreaper
#   docker compose -f deploy/docker-compose.vps.yml up -d --build
FROM python:3.12-slim

# libzbar0 -> pyzbar (lectura de QR) · poppler-utils -> pdf2image
RUN apt-get update && apt-get install -y --no-install-recommends \
        libzbar0 poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencias primero (mejor caché). opencv-headless en vez de opencv-python:
# el servidor no tiene entorno gráfico.
RUN pip install --no-cache-dir \
        fastapi "uvicorn[standard]" python-multipart "mcp>=2" \
        pyzbar opencv-python-headless pillow pdf2image PyMuPDF \
        python-whois tldextract requests reportlab jinja2 click \
        playwright "qrcode[pil]"

# Chromium headless para el sandbox de detonación.
# --with-deps instala las librerías de sistema que necesita Chromium.
RUN playwright install --with-deps chromium

# El paquete (sin reinstalar deps).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

# La BD SQLite vive en el volumen montado aquí (WORKDIR de arranque).
WORKDIR /data
ENV QREAPER_SANDBOX=local
# Indica al sandbox que ya estamos dentro de un contenedor:
# activa --no-sandbox en Chromium y evita intentar Docker-in-Docker.
ENV QREAPER_EN_CONTENEDOR=1

EXPOSE 8000
CMD ["uvicorn", "qreaper.api:app", "--host", "0.0.0.0", "--port", "8000"]
