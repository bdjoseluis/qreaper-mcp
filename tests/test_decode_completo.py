"""
Tests completos para decode.py — cobertura amplia de edge cases.
"""
from pathlib import Path

import pytest
from PIL import Image

from qreaper.decode import decode

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO_LEGITIMO = RAIZ / "datasets" / "legitimos" / "ejemplo.png"
EJEMPLO_MALICIOSO = RAIZ / "datasets" / "maliciosos" / "ejemplo-typosquat.png"


# ── 1. Archivo no existe ────────────────────────────────────────────
def test_decode_archivo_no_existe():
    """Debe lanzar FileNotFoundError si el archivo no existe."""
    with pytest.raises(FileNotFoundError):
        decode("ruta/que/no/existe.png")


# ── 2. Imagen sin QR ────────────────────────────────────────────────
def test_decode_imagen_sin_qr(tmp_path):
    """Debe devolver [] si la imagen no tiene QR."""
    img = Image.new("RGB", (100, 100), "white")
    ruta = tmp_path / "sin_qr.png"
    img.save(ruta)
    assert decode(str(ruta)) == []


# ── 3. QR con texto no-URL (skip — pyzbar no escribe QR) ────────────
@pytest.mark.skip(reason="pyzbar no puede crear QR programáticamente")
def test_decode_qr_con_texto_no_url():
    """Debe devolver [] si el QR contiene texto que no es URL."""
    pass


# ── 4. Múltiples QR / sin duplicados ────────────────────────────────
def test_decode_multiples_urls():
    """Las URLs devueltas no deben tener duplicados."""
    urls = decode(str(EJEMPLO_LEGITIMO))
    assert len(urls) == len(set(urls)), "Hay URLs duplicadas"


# ── 5. Tipo de retorno ──────────────────────────────────────────────
def test_decode_devuelve_lista():
    """decode() debe devolver siempre una lista."""
    urls = decode(str(EJEMPLO_LEGITIMO))
    assert isinstance(urls, list)


def test_decode_elementos_son_strings():
    """Cada elemento de la lista debe ser string."""
    urls = decode(str(EJEMPLO_LEGITIMO))
    assert all(isinstance(u, str) for u in urls)


# ── 6. Contenido URL esperado ───────────────────────────────────────
def test_decode_url_contiene_dominio_esperado():
    """El QR de ejemplo debe contener b-dev.es."""
    urls = decode(str(EJEMPLO_LEGITIMO))
    assert any("b-dev.es" in u for u in urls), (
        f"No se encontró 'b-dev.es' en {urls}"
    )


# ── 7. QR malicioso ────────────────────────────────────────────────
def test_decode_qr_malicioso():
    """El QR malicioso debe ser decodificado correctamente."""
    urls = decode(str(EJEMPLO_MALICIOSO))
    assert len(urls) > 0, "No se decodificó ningún QR malicioso"
    assert any("correos-es.top" in u for u in urls), (
        f"No se encontró 'correos-es.top' en {urls}"
    )


# ── 8. Formatos de imagen soportados ────────────────────────────────
@pytest.mark.parametrize("ext", [".png", ".jpg", ".jpeg", ".bmp", ".tiff"])
def test_decode_formatos_soportados(ext, tmp_path):
    """Debe aceptar múltiples formatos de imagen sin crashear."""
    img = Image.new("RGB", (100, 100), "white")
    ruta = tmp_path / f"test{ext}"
    img.save(ruta)
    result = decode(str(ruta))
    assert isinstance(result, list)


# ── 9. Extensión desconocida ────────────────────────────────────────
def test_decode_extension_desconocida(tmp_path):
    """Extensiones desconocidas deben intentarse como imagen."""
    img = Image.new("RGB", (100, 100), "white")
    tmp = tmp_path / "test_tmp.png"
    img.save(tmp)
    ruta = tmp_path / "test.xyz"
    tmp.rename(ruta)
    result = decode(str(ruta))
    assert isinstance(result, list)


# ── 10. Archivo vacío ──────────────────────────────────────────────
def test_decode_archivo_vacio(tmp_path):
    """Un archivo vacío no debe crashear."""
    ruta = tmp_path / "vacio.png"
    ruta.write_bytes(b"")
    result = decode(str(ruta))
    assert isinstance(result, list)


# ── 11. Path con espacios ──────────────────────────────────────────
def test_decode_path_con_espacios(tmp_path):
    """Debe manejar rutas con espacios."""
    img = Image.new("RGB", (100, 100), "white")
    carpeta = tmp_path / "carpeta con espacios"
    carpeta.mkdir()
    ruta = carpeta / "test.png"
    img.save(ruta)
    result = decode(str(ruta))
    assert isinstance(result, list)


# ── 12. Nombre unicode ─────────────────────────────────────────────
def test_decode_nombre_unicode(tmp_path):
    """Debe manejar nombres de archivo con caracteres especiales."""
    img = Image.new("RGB", (100, 100), "white")
    ruta = tmp_path / "archivo_ñ_á.png"
    img.save(ruta)
    result = decode(str(ruta))
    assert isinstance(result, list)


# ── 14. URLs con formato especial (regex actualizado) ──────────────
def test_es_url_con_puerto():
    """URLs con puerto deben ser aceptadas."""
    from qreaper.decode import _es_url
    assert _es_url("https://evil.com:8443/phish")
    assert _es_url("http://192.168.1.1:80/path")


def test_es_url_con_userinfo():
    """URLs con userinfo (@) deben ser aceptadas."""
    from qreaper.decode import _es_url
    assert _es_url("https://user@evil.com")
    assert _es_url("https://admin:pass@evil.com/path")


def test_es_url_con_ipv4():
    """URLs con IPv4 deben ser aceptadas."""
    from qreaper.decode import _es_url
    assert _es_url("http://192.168.1.1/phish")
    assert _es_url("https://10.0.0.1:8080/path?q=1")


def test_es_url_con_localhost():
    """URLs con hostname simple (localhost) deben ser aceptadas."""
    from qreaper.decode import _es_url
    assert _es_url("http://localhost/path")
    assert _es_url("https://mi-servidor")


def test_es_url_rechaza_texto_no_url():
    """Textos que no son URLs deben ser rechazados."""
    from qreaper.decode import _es_url
    assert not _es_url("hola mundo")
    assert not _es_url("https://")
    assert not _es_url("12345")
    assert not _es_url("")


# ── 14b. Esquemas no-http (deep links) ─────────────────────────────
def test_es_url_acepta_telegram():
    """URLs con esquema telegram:// deben ser aceptadas."""
    from qreaper.decode import _es_url
    assert _es_url("telegram://resolve?domain=soporte_bbva_es")


def test_es_url_acepta_intent():
    """URLs con esquema intent:// deben ser aceptadas."""
    from qreaper.decode import _es_url
    assert _es_url("intent://scan/#Intent;scheme=zxing;package=com.google.zxing.client.android;end")


def test_es_url_acepta_mailto():
    """URLs con esquema mailto: deben ser aceptadas."""
    from qreaper.decode import _es_url
    assert _es_url("mailto:user@example.com")


def test_es_url_acepta_upi():
    """URLs con esquema upi:// deben ser aceptadas."""
    from qreaper.decode import _es_url
    assert _es_url("upi://pay?pa=merchant@upi")


def test_es_url_acepta_wifi():
    """URLs con esquema WIFI: deben ser aceptadas."""
    from qreaper.decode import _es_url
    assert _es_url("WIFI:T:WPA;S:MiRed;P:clave123;;")


# ── 14c. Normalizacion de URLs sin esquema ──────────────────────────
def test_extraer_urls_normaliza_dominio():
    """Dominios sin esquema deben normalizarse a https://."""
    from qreaper.decode import _extraer_urls
    urls = _extraer_urls(["correos-es.top/pago"])
    assert urls == ["https://correos-es.top/pago"]


def test_extraer_urls_acepta_http():
    """URLs con http:// se mantienen sin cambios."""
    from qreaper.decode import _extraer_urls
    urls = _extraer_urls(["http://correos-es.top/pago"])
    assert urls == ["http://correos-es.top/pago"]


def test_extraer_urls_acepta_telegram():
    """URLs con esquema telegram:// pasan sin normalizar."""
    from qreaper.decode import _extraer_urls
    urls = _extraer_urls(["telegram://resolve?domain=soporte_bbva_es"])
    assert urls == ["telegram://resolve?domain=soporte_bbva_es"]


# ── 14d. Fragmentos descartados (QR partidos) ──────────────────────
def test_extraer_urls_descarta_fragmentos_no_url():
    """Fragmentos que no son URL ni dominio se descartan con log."""
    from qreaper.decode import _extraer_urls
    urls = _extraer_urls(["hola mundo", "texto random"])
    assert urls == []


def test_extraer_urls_no_duplica():
    """No debe haber URLs duplicadas en la salida."""
    from qreaper.decode import _extraer_urls
    urls = _extraer_urls(["https://example.com", "https://example.com", "example.com"])
    assert urls == ["https://example.com"]


# ── 14e. QR partidos (structured append) ──────────────────────────
def test_extraer_urls_concatena_fragmentos():
    """Fragmentos que forman una URL al concatenarse deben unirse."""
    from qreaper.decode import _extraer_urls
    # QR partido: "https://bit.ly/xyz" viene como ["https://bit.", "ly/xyz"]
    urls = _extraer_urls(["https://bit.", "ly/xyz"])
    assert urls == ["https://bit.ly/xyz"]


def test_extraer_urls_concatena_fragmentos_sin_esquema():
    """Fragmentos sin esquema que forman un dominio al concatenarse."""
    from qreaper.decode import _extraer_urls
    # QR partido: "correos-es.top/pago" viene como ["correos-es.", "top/pago"]
    urls = _extraer_urls(["correos-es.", "top/pago"])
    assert urls == ["https://correos-es.top/pago"]


def test_extraer_urls_no_concatenafragmentos_invalidos():
    """Fragmentos que no forman URL al concatenarse se descartan."""
    from qreaper.decode import _extraer_urls
    # Fragmentos sin puntos ni esquema: no pueden formar URL
    urls = _extraer_urls(["12345", "abcdef", "xyz"])
    assert urls == []


def test_extraer_urls_mezcla_urls_y_fragmentos():
    """Mezcla de URLs completas y fragmentos de otro QR partido."""
    from qreaper.decode import _extraer_urls
    # URL completa + fragmentos de otro QR partido
    urls = _extraer_urls(["https://example.com", "https://bit.", "ly/xyz"])
    assert "https://example.com" in urls
    assert "https://bit.ly/xyz" in urls
    assert len(urls) == 2


# ── 15. Soporte para emails .eml ──────────────────────────────────
DATASETS_TEST = RAIZ / "datasets" / "test"


def test_decode_phishing_correo():
    """Debe decodificar QR de un email .eml con imagen adjunta."""
    urls = decode(str(DATASETS_TEST / "phishing_correo.eml"))
    assert len(urls) > 0, "No se encontraron URLs en el email phishing"
    assert any("correos-es.top" in u for u in urls), f"Se esperaba 'correos-es.top' en {urls}"


def test_decode_legitimo_correo():
    """Debe decodificar QR de un email .eml legítimo."""
    urls = decode(str(DATASETS_TEST / "legitimo_correo.eml"))
    assert len(urls) > 0, "No se encontraron URLs en el email legítimo"
    assert any("b-dev.es" in u for u in urls), f"Se esperaba 'b-dev.es' en {urls}"


def test_decode_multiples_adjuntos():
    """Debe decodificar QR de múltiples adjuntos en un email."""
    urls = decode(str(DATASETS_TEST / "phishing_multiples.eml"))
    assert len(urls) >= 2, f"Se esperaban >=2 URLs, se obtuvieron {len(urls)}: {urls}"


# ── 16. Soporte para PDFs ─────────────────────────────────────────
def test_decode_pdf_phishing():
    """Debe decodificar QR de un PDF con QR embebido."""
    urls = decode(str(DATASETS_TEST / "phishing_documento.pdf"))
    assert len(urls) > 0, "No se encontraron URLs en el PDF phishing"
    assert any("bbva-seguridad.top" in u for u in urls), f"Se esperaba 'bbva-seguridad.top' en {urls}"


def test_decode_pdf_legitimo():
    """Debe decodificar QR de un PDF legítimo."""
    urls = decode(str(DATASETS_TEST / "legitimo_documento.pdf"))
    assert len(urls) > 0, "No se encontraron URLs en el PDF legítimo"
    assert any("google.com" in u for u in urls), f"Se esperaba 'google.com' en {urls}"


# ── 17. Temp files cleanup ────────────────────────────────────────
def test_decode_eml_limpia_temporales(tmp_path):
    """Los archivos temporales generados al procesar PDFs en .eml deben limpiarse."""
    from email.message import EmailMessage

    # Crear un .eml con un PDF adjunto (payload arbitrario — no necesita ser PDF real)
    eml = EmailMessage()
    eml["Subject"] = "test"
    eml["From"] = "test@test.com"
    eml["To"] = "dst@test.com"
    eml.add_attachment(b"fake-pdf-content", maintype="application", subtype="pdf")

    ruta_eml = tmp_path / "test.eml"
    ruta_eml.write_bytes(eml.as_bytes())

    import tempfile
    temp_dir = Path(tempfile.gettempdir())

    # Limpiar huérfanos de tests anteriores
    for f in temp_dir.glob("tmp*.pdf"):
        try:
            f.unlink()
        except OSError:
            pass

    decode(str(ruta_eml))

    nuevos = list(temp_dir.glob("tmp*.pdf"))
    assert not nuevos, f"Archivos temporales no limpiados: {nuevos}"
