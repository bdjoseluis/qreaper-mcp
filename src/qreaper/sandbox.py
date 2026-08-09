"""
Módulo 3 — Sandbox de detonación  ·  Responsable: Jose

Objetivo: abrir la URL en navegador headless aislado y observar qué hace.
Lee el contrato en CONTRATOS.md antes de empezar.
"""
from __future__ import annotations


def detonar(url: str) -> dict:
    """Abre la URL en un navegador headless aislado y recoge evidencias.

    TODO (Jose):
      - Playwright headless (dentro de Docker para aislar)
      - seguir redirecciones y guardar la cadena
      - screenshot de la página final
      - detectar formularios de login (inputs password)
    """
    raise NotImplementedError("Jose: implementar detonar()")
