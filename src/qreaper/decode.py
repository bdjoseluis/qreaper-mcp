"""
Modulo 1 — Ingesta + Decode  ·  Responsable: Andres

Objetivo: de un archivo (email .eml, PDF o imagen) -> extraer QR -> devolver URLs.
Lee el contrato en CONTRATOS.md antes de empezar.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
from email import policy
from email.parser import BytesParser
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode, PyZbarError

__all__ = ["decode"]

log = logging.getLogger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif"}
PDF_EXT = ".pdf"
EML_EXT = ".eml"

_URL_RE = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9+.\-]*://"  # esquema con ://
    r"[^\s]+"                          # contenido sin whitespace
    r"(?<!\.)"                         # no termina en punto (URL incompleta)
    r"$"
)

_MAILTO_TEL_RE = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9+.\-]*:(?!//)[^\s]+"  # esquema con : pero sin // (mailto:, tel:, WIFI:)
)

_DOMINIO_RE = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9.-]*"    # label con puntos y guiones
    r"\.[a-zA-Z]{2,4}"               # .TLD (2-4 letras, como los TLDs mas comunes)
    r"(:\d{1,5})?"                   # puerto opcional
    r"(?:/[^\s]*)?$"                 # path opcional
)

MAX_PAGINAS_PDF = 50
PDF_DPI = 300


def _es_url(texto: str) -> bool:
    """Devuelve True si el texto parece una URL."""
    texto = texto.strip()
    return _URL_RE.fullmatch(texto) is not None or _MAILTO_TEL_RE.fullmatch(texto) is not None


def _normalizar_url(texto: str) -> str | None:
    """Si el texto parece una URL sin esquema, le agrega https://.

    Devuelve la URL normalizada o None si no parece URL.
    """
    if _es_url(texto):
        return texto
    if _DOMINIO_RE.fullmatch(texto):
        return "https://" + texto
    return None


def _intentar_concatenar(fragmentos: list[str]) -> str | None:
    """Intenta concatenar fragmentos y verificar si forman una URL valida.

    Los QR partidos (structured append) vienen en fragmentos consecutivos.
    Esta funcion prueba a unirlos directamente (sin separador) y ver si el
    resultado es una URL.
    """
    if not fragmentos or len(fragmentos) < 2:
        return None

    # Concatenacion directa (como viene del structured append)
    candidata = "".join(fragmentos)
    return _normalizar_url(candidata)


def _extraer_urls(datos_qr: list[str]) -> list[str]:
    """Filtra solo las cadenas que son URLs, normaliza y elimina duplicados.

    Tambien intenta reconstruir URLs fragmentadas (QR partidos/structured append).
    """
    urls: list[str] = []
    vistos: set[str] = set()
    fragmentos_pendientes: list[str] = []

    for dato in datos_qr:
        texto = dato.strip()
        if not texto:
            continue

        normalizada = _normalizar_url(texto)
        if normalizada is not None:
            # Antes de agregar la URL actual, intentar concatenar fragmentos pendientes
            if fragmentos_pendientes:
                concatenada = _intentar_concatenar(fragmentos_pendientes)
                if concatenada and concatenada not in vistos:
                    urls.append(concatenada)
                    vistos.add(concatenada)
                    log.debug(
                        "Fragmentos concatenados exitosamente: %s -> %s",
                        fragmentos_pendientes, concatenada,
                    )
                else:
                    log.debug(
                        "Descartando fragmentos no-URL no concatenables: %s",
                        fragmentos_pendientes,
                    )
                fragmentos_pendientes.clear()

            if normalizada not in vistos:
                urls.append(normalizada)
                vistos.add(normalizada)
        else:
            fragmentos_pendientes.append(texto)

    # Al final, intentar concatenar los fragmentos pendientes restantes
    if fragmentos_pendientes:
        concatenada = _intentar_concatenar(fragmentos_pendientes)
        if concatenada and concatenada not in vistos:
            urls.append(concatenada)
            vistos.add(concatenada)
            log.debug(
                "Fragmentos finales concatenados: %s -> %s",
                fragmentos_pendientes, concatenada,
            )
        else:
            log.debug(
                "Descartando fragmentos finales no concatenables: %s",
                fragmentos_pendientes,
            )

    return urls


def _preprocesar_imagen(img: np.ndarray) -> list[np.ndarray]:
    """Aplica varias tecnicas de preprocesamiento para mejorar deteccion QR.

    Devuelve una lista de imagenes preprocesadas para intentar decodificar.
    """
    resultados: list[np.ndarray] = []

    # 1. Original (si viene en color, convertir a escala de grises)
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

    # 2. Binarizacion Otsu
    _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    resultados.append(binaria)

    # 3. Binarizacion inversa
    _, binaria_inv = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    resultados.append(binaria_inv)

    # 4. Redimensionar si la imagen es muy pequena (pyzbar necesita ~200px min)
    h, w = gris.shape[:2]
    if min(h, w) < 300:
        factor = 300 / min(h, w)
        redim = cv2.resize(gris, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
        resultados.append(redim)

    # 5. Ecualizacion de histograma (CLAHE) para mejorar contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    ecualizada = clahe.apply(gris)
    resultados.append(ecualizada)

    # 6. Adaptive threshold
    adaptativa = cv2.adaptiveThreshold(
        gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 10
    )
    resultados.append(adaptativa)

    return resultados


def _decodificar_qr_de_imagen(img: np.ndarray) -> list[str]:
    """Intenta decodificar QR de una imagen usando pyzbar.

    Aplica preprocesamiento para maximizar la deteccion.
    """
    textos: list[str] = []

    # Convertir BGR a RGB si es necesario (pyzbar espera RGB)
    if len(img.shape) == 3 and img.shape[2] == 3:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    elif len(img.shape) == 3 and img.shape[2] == 4:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    else:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB) if len(img.shape) == 2 else img

    try:
        resultados = pyzbar_decode(img_rgb)
        for r in resultados:
            try:
                texto = r.data.decode("utf-8").strip()
            except UnicodeDecodeError:
                texto = r.data.decode("latin-1").strip()
            if texto:
                textos.append(texto)
    except PyZbarError:
        log.debug("pyzbar no pudo decodificar QR en la imagen")
    except Exception as e:
        log.warning("Error inesperado decodificando QR: %s", e)

    return textos


def _procesar_imagen(ruta: str) -> list[str]:
    """Procesa un archivo de imagen, decodificando todos los QR encontrados."""
    textos: list[str] = []

    # Leer imagen con OpenCV
    img = cv2.imread(ruta)
    if img is None:
        # Intentar con PIL como fallback
        try:
            pil_img = Image.open(ruta)
            img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        except Exception as e:
            log.error("No se pudo leer la imagen %s: %s", ruta, e)
            return []

    # Decodificar QR de la imagen original
    textos.extend(_decodificar_qr_de_imagen(img))

    # Intentar con preprocesamiento para capturar QRs adicionales
    for img_proc in _preprocesar_imagen(img):
        textos.extend(_decodificar_qr_de_imagen(img_proc))

    return textos


def _procesar_pdf(ruta: str) -> list[str]:
    """Convierte paginas del PDF a imagenes y decodifica QR."""
    textos: list[str] = []

    # Intentar con pdf2image (poppler) primero
    try:
        from pdf2image import convert_from_path
        imagenes = convert_from_path(ruta, dpi=PDF_DPI, first_page=1, last_page=MAX_PAGINAS_PDF)
        for imagen_pil in imagenes:
            img_array = cv2.cvtColor(np.array(imagen_pil.convert("RGB")), cv2.COLOR_RGB2BGR)
            textos.extend(_decodificar_qr_de_imagen(img_array))
        return textos
    except Exception as e:
        log.debug("pdf2image fallo, intentando con PyMuPDF: %s", e)

    # Fallback: usar PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(ruta)
        for i, page in enumerate(doc):
            if i >= MAX_PAGINAS_PDF:
                break
            pix = page.get_pixmap(dpi=PDF_DPI)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            if pix.n == 4:
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            else:
                img_bgr = img
            textos.extend(_decodificar_qr_de_imagen(img_bgr))
        doc.close()
    except Exception:
        log.error("Error procesando PDF %s", ruta)

    return textos


def _procesar_eml(ruta: str) -> list[str]:
    """Parsea un email .eml y extrae QR de las imagenes adjuntas."""
    textos: list[str] = []

    try:
        with open(ruta, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)
    except Exception as e:
        log.error("Error parseando email %s: %s", ruta, e)
        return []

    for parte in msg.walk():
        content_type = parte.get_content_type()
        if content_type and content_type.startswith("image/"):
            try:
                payload = parte.get_payload(decode=True)
                if payload:
                    arr = np.frombuffer(payload, dtype=np.uint8)
                    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if img is not None:
                        textos.extend(_decodificar_qr_de_imagen(img))
            except Exception as e:
                log.debug("Error procesando adjunto del email: %s", e)
                continue
        elif content_type == "application/pdf":
            payload = parte.get_payload(decode=True)
            if not payload:
                continue
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            try:
                tmp.write(payload)
                tmp.flush()
                tmp.close()
                textos.extend(_procesar_pdf(tmp.name))
            except Exception as e:
                log.debug("Error procesando PDF adjunto del email: %s", e)
            finally:
                # En Windows, fitz puede mantener el handle abierto aunque
                # falle. Renombrar primero rompe el lock del archivo.
                try:
                    staging = tmp.name + ".del"
                    os.rename(tmp.name, staging)
                    os.unlink(staging)
                except OSError:
                    log.debug("No se pudo eliminar temporal %s", tmp.name)

    return textos


def decode(ruta_archivo: str) -> list[str]:
    """Extrae y decodifica los codigos QR de un archivo. Devuelve lista de URLs.

    Soporta: imagenes (.png, .jpg, .jpeg, .bmp, .gif, .tiff), PDFs y emails (.eml).
    """
    ruta = Path(ruta_archivo)

    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_archivo}")

    ext = ruta.suffix.lower()

    if ext in IMAGE_EXTS:
        textos = _procesar_imagen(str(ruta))
    elif ext == PDF_EXT:
        textos = _procesar_pdf(str(ruta))
    elif ext == EML_EXT:
        textos = _procesar_eml(str(ruta))
    else:
        # Intentar como imagen por defecto
        log.warning("Extensión desconocida: %s. Intentando como imagen.", ext)
        textos = _procesar_imagen(str(ruta))

    urls = _extraer_urls(textos)
    return urls


if __name__ == "__main__":
    import sys

    print(decode(sys.argv[1]))
