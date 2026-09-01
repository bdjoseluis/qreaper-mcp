"""
Genera fixtures de campanas reales de phishing por QR.

Uso:
    python scripts/generar_fixtures_qr.py

Lee tests/fixtures/campanas_reales/campanas.csv y por cada fila crea:
    - tests/fixtures/campanas_reales/<slug>.eml  (email con el QR adjunto)
    - tests/fixtures/campanas_reales/<slug>.pdf  (PDF con el QR embebido)
    - tests/fixtures/campanas_reales/<slug>.png  (el QR suelto, por si acaso)

Formato del CSV (con cabecera):
    slug,marca,asunto,cuerpo,url_maliciosa

Ejemplo:
    bbva-verificar-cuenta,BBVA,Verifique su cuenta,Estimado cliente...,http://bbva-verify.tk/login
"""

import csv
import io
from email.message import EmailMessage
from pathlib import Path

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

BASE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "campanas_reales"


def hacer_qr_png(url: str) -> bytes:
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def hacer_eml(slug: str, marca: str, asunto: str, cuerpo: str, qr_png: bytes) -> bytes:
    msg = EmailMessage()
    msg["From"] = f"{marca} <no-reply@{marca.lower()}.es>"
    msg["To"] = "victima@ejemplo.com"
    msg["Subject"] = asunto
    msg.set_content(cuerpo + "\n\nEscanee el codigo QR adjunto para continuar.")
    msg.add_attachment(qr_png, maintype="image", subtype="png", filename=f"{slug}.png")
    return bytes(msg)


def hacer_pdf(marca: str, asunto: str, cuerpo: str, qr_png: bytes) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ancho, alto = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * 28, alto - 3 * 28, marca)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * 28, alto - 4 * 28, asunto)
    c.setFont("Helvetica", 10)
    y = alto - 6 * 28
    for linea in cuerpo.split("\n"):
        c.drawString(2 * 28, y, linea)
        y -= 14
    qr_img = ImageReader(io.BytesIO(qr_png))
    c.drawImage(qr_img, 2 * 28, y - 200, width=180, height=180)
    c.showPage()
    c.save()
    return buf.getvalue()


def main() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    csv_path = BASE / "campanas.csv"
    if not csv_path.exists():
        _crear_csv_de_ejemplo(csv_path)
        print(f"[i] Creado CSV de ejemplo en {csv_path}. Rellena mas filas y vuelve a ejecutar.")

    with csv_path.open(encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))

    for fila in filas:
        slug = fila["slug"].strip()
        qr = hacer_qr_png(fila["url_maliciosa"].strip())
        (BASE / f"{slug}.png").write_bytes(qr)
        (BASE / f"{slug}.eml").write_bytes(
            hacer_eml(slug, fila["marca"], fila["asunto"], fila["cuerpo"], qr)
        )
        (BASE / f"{slug}.pdf").write_bytes(
            hacer_pdf(fila["marca"], fila["asunto"], fila["cuerpo"], qr)
        )
        print(f"[ok] {slug}: png + eml + pdf")

    print(f"\n{len(filas)} campanas generadas en {BASE}")


def _crear_csv_de_ejemplo(path: Path) -> None:
    ejemplos = [
        {
            "slug": "bbva-verificar-cuenta",
            "marca": "BBVA",
            "asunto": "Verifique su cuenta antes de 24h",
            "cuerpo": "Estimado cliente,\nHemos detectado accesos sospechosos.\nEscanee el QR para verificar su identidad.",
            "url_maliciosa": "http://bbva-verify.tk/login",
        },
        {
            "slug": "correos-paquete-retenido",
            "marca": "Correos",
            "asunto": "Paquete retenido - pago pendiente 1.99EUR",
            "cuerpo": "Su paquete esta retenido en aduana.\nPague la tasa escaneando el QR.",
            "url_maliciosa": "http://correos-pago.duckdns.org/",
        },
        {
            "slug": "dgt-multa-pendiente",
            "marca": "DGT",
            "asunto": "Notificacion de multa 84.50 EUR",
            "cuerpo": "Tiene una multa pendiente por exceso de velocidad.\nConsulte y pague por QR.",
            "url_maliciosa": "http://dgt-multas-online.tk/consulta",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ejemplos[0]))
        w.writeheader()
        w.writerows(ejemplos)


if __name__ == "__main__":
    main()
