"""
Orquestador  ·  Responsable: Jose (integración)

Une los 6 módulos. Cada persona implementa SU módulo; esto solo los encadena.
"""
from __future__ import annotations

from . import decode, analisis_url, sandbox, scoring, informe


def analizar_archivo(ruta_archivo: str, formato_informe: str = "pdf") -> list[dict]:
    """Pipeline completo: archivo → [resultados por cada URL encontrada]."""
    resultados = []
    for url in decode.decode(ruta_archivo):
        senales = analisis_url.analizar_url(url)
        detonacion = sandbox.detonar(url)
        veredicto = scoring.puntuar(senales, detonacion)
        resultado = {
            "url": url,
            "senales": senales,
            "sandbox": detonacion,
            "scoring": veredicto,
        }
        resultado["informe"] = informe.generar_informe(resultado, formato_informe)
        resultados.append(resultado)
    return resultados
