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
