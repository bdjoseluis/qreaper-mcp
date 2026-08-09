"""
Módulo 1 — Ingesta + Decode  ·  Responsable: Andrés

Objetivo: de un archivo (email .eml, PDF o imagen) → extraer QR → devolver URLs.
Lee el contrato en CONTRATOS.md antes de empezar.
"""
from __future__ import annotations


def decode(ruta_archivo: str) -> list[str]:
    """Extrae y decodifica los códigos QR de un archivo. Devuelve lista de URLs.

    TODO (Andrés):
      - Detectar el tipo de archivo (.eml / .pdf / imagen)
      - Si es email: extraer imágenes adjuntas
      - Si es PDF: extraer imágenes (pdf2image)
      - Decodificar QR con pyzbar (preprocesar con OpenCV si hace falta)
      - Soportar QR partidos / anidados
      - Devolver URLs únicas
    """
    raise NotImplementedError("Andrés: implementar decode()")


if __name__ == "__main__":
    import sys
    print(decode(sys.argv[1]))
