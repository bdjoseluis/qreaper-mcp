"""
Módulo 6 — Interfaz (CLI)  ·  Responsable: 5ª persona

Objetivo: interfaz de usuario. NO implementa lógica de análisis.
"""
from __future__ import annotations

import click

from . import pipeline


@click.group()
def cli():
    """QReaper - Analizador Anti-Quishing."""


@cli.command()
@click.argument("ruta_archivo")
@click.option("--formato", default="pdf", help="pdf | json | html")
def analizar(ruta_archivo, formato):
    """Analiza un archivo (email/PDF/imagen) en busca de quishing."""
    # TODO (5ª persona): formatear la salida por consola de forma bonita
    resultados = pipeline.analizar_archivo(ruta_archivo, formato)
    for r in resultados:
        click.echo(r)


if __name__ == "__main__":
    cli()
