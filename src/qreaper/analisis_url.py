"""
Módulo 2 — Análisis estático de URL  ·  Responsable: Alex

Objetivo: dada una URL, buscarle pegas SIN abrirla. Devuelve dict de señales.
Lee el contrato en CONTRATOS.md antes de empezar.
"""
from __future__ import annotations


def analizar_url(url: str) -> dict:
    """Analiza una URL de forma estática y devuelve señales de riesgo.

    TODO (Alex):
      - whois: edad del dominio
      - clasificar TLD por riesgo
      - typosquatting / homoglifos contra lista de marcas
      - expandir acortadores
      - detectar deep-links (telegram://, intent://)
    """
    raise NotImplementedError("Alex: implementar analizar_url()")


if __name__ == "__main__":
    import sys
    print(analizar_url(sys.argv[1]))
