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
    r"^https?://"
    r"(?:[a-zA-Z0-9._~!$&'()*+,;=:@-]*@)?"  # userinfo opcional
    r"(?:"                                     # host (alternativas):
        r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}"  # dominio
        r"|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"  # IPv4
        r"|[a-zA-Z0-9-]+"                         # hostname simple (localhost, etc.)
    r")"
    r"(?::\d{1,5})?"                       # puerto opcional
    r"(?:/[^\s]*)?$"                       # path opcional
)

MAX_PAGINAS_PDF = 50
PDF_DPI = 300


def _es_url(texto: str) -> bool:
    """Devuelve True si el texto parece una URL."""
    texto = texto.strip()
    return _URL_RE.fullmatch(texto) is not None


def _extraer_urls(datos_qr: list[str]) -> list[str]:
    """Filtra solo las cadenas que son URLs y elimina duplicados."""
    urls: list[str] = []
    vistos: set[str] = set()
    for dato in datos_qr:
        texto = dato.strip()
        if _es_url(texto) and texto not in vistos:
            urls.append(texto)
            vistos.add(texto)
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
    except Exception as e:
        log.error("Error procesando PDF %s: %s", ruta, e)

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
            try:
                payload = parte.get_payload(decode=True)
                if payload:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(payload)
                        tmp.flush()
                    try:
                        textos.extend(_procesar_pdf(tmp.name))
                    finally:
                        os.unlink(tmp.name)
            except Exception as e:
                log.debug("Error procesando PDF adjunto del email: %s", e)
                continue

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
