"""
Módulo — Servidor MCP  ·  Responsable: Jose (integración)

Expone el motor de QReaper como herramientas MCP (Model Context Protocol)
invocables desde un cliente como Claude. Es la misma lógica que el CLI y la
API REST, pero envuelta como *tools* que un asistente puede llamar.

Herramientas publicadas:
    - analizar_url(url)           → veredicto de riesgo de una URL
    - analizar_archivo(ruta)      → analiza un fichero local con QR
    - historial(limite, veredicto)→ consulta los análisis guardados

Arranque (transporte stdio, el que usa Claude Desktop / Claude Code):

    qreaper-mcp
    # o bien:  python -m qreaper.mcp_server

Registro en Claude Code:

    claude mcp add qreaper -- qreaper-mcp
"""
from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

from . import db, pipeline

log = logging.getLogger("qreaper.mcp")

mcp = MCPServer("qreaper")


def _resumen(resultado: dict) -> dict:
    """Compacta el resultado del pipeline a lo esencial para el asistente.

    El dict completo trae sandbox, señales e informe; para una tool conviene
    devolver algo legible y barato en tokens, conservando lo accionable.
    """
    scoring = resultado.get("scoring") or {}
    sandbox = resultado.get("sandbox") or {}
    return {
        "url": resultado.get("url"),
        "veredicto": scoring.get("veredicto", "DESCONOCIDO"),
        "nota": scoring.get("nota"),
        "motivos": scoring.get("motivos") or [],
        "url_final": sandbox.get("url_final"),
        "errores": resultado.get("errores") or {},
    }


@mcp.tool()
def analizar_url(url: str) -> dict:
    """Analiza una URL sospechosa y devuelve su veredicto de riesgo anti-quishing.

    Args:
        url: dirección a analizar (por ejemplo, la que esconde un QR).

    Returns:
        Resumen con veredicto (PELIGRO/SOSPECHOSO/SEGURO/DESCONOCIDO), nota
        0-100, motivos y la URL final tras redirecciones.
    """
    log.info("[MCP] analizar_url: %s", url)
    resultado = pipeline.analizar_url_suelta(url, formato_informe=None)
    return _resumen(resultado)


@mcp.tool()
def analizar_archivo(ruta: str) -> dict:
    """Analiza un archivo local (imagen, PDF o email .eml) buscando QR maliciosos.

    Args:
        ruta: ruta en el sistema de ficheros del servidor.

    Returns:
        Lista de resúmenes, uno por cada URL encontrada en los QR del archivo.
    """
    log.info("[MCP] analizar_archivo: %s", ruta)
    resultados = pipeline.analizar_archivo(ruta, formato_informe=None)
    return {
        "ruta": ruta,
        "urls_encontradas": len(resultados),
        "resultados": [_resumen(r) for r in resultados],
    }


@mcp.tool()
def historial(limite: int = 20, veredicto: str | None = None) -> dict:
    """Consulta los últimos análisis guardados en la base de datos.

    Args:
        limite: número máximo de registros a devolver (por defecto 20).
        veredicto: filtro opcional (PELIGRO/SOSPECHOSO/SEGURO/DESCONOCIDO).

    Returns:
        Los registros más recientes primero.
    """
    registros = db.listar()
    if veredicto:
        v = veredicto.upper()
        registros = [r for r in registros if (r.get("veredicto") or "").upper() == v]
    registros = registros[: max(1, limite)]
    return {"total": len(registros), "analisis": registros}


def main() -> None:
    """Punto de entrada del script `qreaper-mcp`: arranca el servidor por stdio."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    mcp.run()


if __name__ == "__main__":
    main()
