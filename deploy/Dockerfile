# Imagen de la API + web de QReaper para el VPS.
#
# Incluye lo necesario para leer QR (decode), analizar la URL (url) y generar
# informes, MÁS la capa API/MCP. NO incluye el sandbox (playwright/Docker):
# en el despliegue compartido se corre con QREAPER_SANDBOX=off para no detonar
# URLs hostiles en el host de producción. El sandbox completo se usa en local.
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
        python-whois tldextract requests reportlab jinja2 click

# El paquete (sin reinstalar deps).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

# La BD SQLite vive en el volumen montado aquí (WORKDIR de arranque).
WORKDIR /data
ENV QREAPER_SANDBOX=off

EXPOSE 8000
CMD ["uvicorn", "qreaper.api:app", "--host", "0.0.0.0", "--port", "8000"]
