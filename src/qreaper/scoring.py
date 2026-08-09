"""
Módulo 4 — Scoring  ·  Responsable: Jose

Objetivo: combinar señales estáticas + dinámicas → nota de riesgo + veredicto.
Lee el contrato en CONTRATOS.md antes de empezar.
"""
from __future__ import annotations


def puntuar(senales_url: dict, resultado_sandbox: dict) -> dict:
    """Combina todas las señales en una nota 0-100 y un veredicto.

    TODO (Jose):
      - ponderar cada señal (dominio nuevo, typosquat, form login, ...)
      - devolver {nota, veredicto, motivos}
    """
    raise NotImplementedError("Jose: implementar puntuar()")
