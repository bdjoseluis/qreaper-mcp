"""
Módulo 5 — Informe  ·  Responsable: Andrés

Objetivo: convertir el resultado completo en un informe PDF/JSON/HTML.
Lee el contrato en CONTRATOS.md antes de empezar.
"""
from __future__ import annotations


def generar_informe(resultado: dict, formato: str = "pdf") -> str:
    """Genera el informe y devuelve la ruta del archivo.

    TODO (Andrés):
      - plantilla del informe (reportlab para PDF, jinja2 para HTML)
      - incluir URL, señales, screenshot, nota y recomendación
      - soportar formato "pdf" | "json" | "html"
    """
    raise NotImplementedError("Andrés: implementar generar_informe()")
