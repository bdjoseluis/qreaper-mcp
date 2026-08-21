"""
Genera fixtures de prueba para Sprint 2 de QReaper.
Crea archivos .eml y .pdf con códigos QR embebidos.
"""
import qrcode
import os
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile

RAIZ = Path(__file__).resolve().parent.parent
DATASETS_TEST = RAIZ / "datasets" / "test"
DATASETS_TEST.mkdir(parents=True, exist_ok=True)


def crear_qr(url: str, ruta_salida: str):
    """Crea una imagen PNG con un código QR."""
    img = qrcode.make(url)
    img.save(ruta_salida)


def crear_eml(asunto: str, remitente: str, adjuntos: list[tuple[str, str]], ruta_salida: str):
    """Crea un archivo .eml con imágenes adjuntas."""
    msg = MIMEMultipart()
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = 'victima@ejemplo.com'
    
    # Agregar cuerpo del email
    body = MIMEText('Por favor revisa el documento adjunto.', 'plain')
    msg.attach(body)
    
    # Agregar adjuntos
    for ruta_qr, nombre_adjunto in adjuntos:
        with open(ruta_qr, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-Disposition', 'attachment', filename=nombre_adjunto)
            msg.attach(img)
    
    with open(ruta_salida, 'w') as f:
        f.write(msg.as_string())


def crear_pdf_con_qr(url_qr: str, ruta_pdf: str):
    """Crea un PDF con un código QR embebido."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        crear_qr(url_qr, tmp.name)
        tmp_path = tmp.name
    
    try:
        c = canvas.Canvas(ruta_pdf, pagesize=A4)
        c.setFont("Helvetica", 16)
        c.drawString(100, 700, "Documento oficial - Escanea el código QR")
        c.drawImage(ImageReader(tmp_path), 200, 400, width=200, height=200)
        c.setFont("Helvetica", 10)
        c.drawString(200, 380, f"URL: {url_qr}")
        c.save()
    finally:
        os.unlink(tmp_path)


def main():
    print("Generando fixtures de prueba...")
    
    # Crear directorio temporal para QRs
    tmp_dir = RAIZ / "datasets" / "test" / "_tmp_qr"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Phishing correo (1 adjunto)
    qr1 = tmp_dir / "qr_phishing.png"
    crear_qr("https://correos-es.top/pago-pendiente", str(qr1))
    crear_eml(
        asunto="Factura pendiente de pago",
        remitente="factura@correos-es.top",
        adjuntos=[(str(qr1), "factura.png")],
        ruta_salida=str(DATASETS_TEST / "phishing_correo.eml")
    )
    print("  ✅ phishing_correo.eml")
    
    # 2. Legítimo correo (1 adjunto)
    qr2 = tmp_dir / "qr_legitimo.png"
    crear_qr("https://b-dev.es/", str(qr2))
    crear_eml(
        asunto="Bienvenido a nuestro servicio",
        remitente="noreply@b-dev.es",
        adjuntos=[(str(qr2), "bienvenida.png")],
        ruta_salida=str(DATASETS_TEST / "legitimo_correo.eml")
    )
    print("  ✅ legitimo_correo.eml")
    
    # 3. Phishing múltiples adjuntos
    qr3a = tmp_dir / "qr_correos.png"
    qr3b = tmp_dir / "qr_bbva.png"
    crear_qr("https://correos-es.top/factura", str(qr3a))
    crear_qr("https://bbva-seguridad.top/login", str(qr3b))
    crear_eml(
        asunto="Documentos importantes",
        remitente="documentos@correo-es.top",
        adjuntos=[
            (str(qr3a), "factura_correos.png"),
            (str(qr3b), "acceso_bbva.png")
        ],
        ruta_salida=str(DATASETS_TEST / "phishing_multiples.eml")
    )
    print("  ✅ phishing_multiples.eml")
    
    # 4. PDF phishing
    crear_pdf_con_qr(
        "https://bbva-seguridad.top/login",
        str(DATASETS_TEST / "phishing_documento.pdf")
    )
    print("  ✅ phishing_documento.pdf")
    
    # 5. PDF legítimo
    crear_pdf_con_qr(
        "https://google.com",
        str(DATASETS_TEST / "legitimo_documento.pdf")
    )
    print("  ✅ legitimo_documento.pdf")
    
    # Limpiar QRs temporales
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    
    print(f"\nTodos los fixtures generados en: {DATASETS_TEST}")


if __name__ == "__main__":
    main()
