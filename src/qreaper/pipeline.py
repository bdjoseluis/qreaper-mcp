"""
Orquestador  ·  Responsable: Jose (integración)

Une los 6 módulos. Cada persona implementa SU módulo; esto solo los encadena.

Regla de oro: **que falle un módulo no puede tumbar el análisis entero**.
Mientras los compañeros van terminando, sus módulos lanzan
``NotImplementedError``; el pipeline lo recoge, sigue adelante con lo que sí
funciona y deja constancia en ``errores``. Así se puede probar la cadena
completa desde hoy sin esperar a que estén los cinco módulos.
"""
from __future__ import annotations

import logging
import os

from . import analisis_url, db, decode, informe, sandbox, scoring

log = logging.getLogger(__name__)


def _sandbox_activo() -> bool:
    """El sandbox detona URLs reales; en despliegues compartidos se apaga.

    Se controla con la variable de entorno ``QREAPER_SANDBOX``: cualquiera de
    ``off``/``0``/``false``/``no`` la desactiva (el análisis sigue por señales
    de URL + scoring). Por defecto está activo, como en local.
    """
    return os.getenv("QREAPER_SANDBOX", "on").strip().lower() not in {
        "off", "0", "false", "no",
    }

#: Claves que promete ``analisis_url.analizar_url()`` en CONTRATOS.md.
#: Si el módulo falla, rellenamos con None para que scoring no se entere.
CLAVES_SENALES = (
    "url", "edad_dominio_dias", "tld_riesgo", "es_typosquat",
    "marca_suplantada", "es_acortador", "url_expandida", "deep_link",
)


def _senales_vacias(url: str) -> dict:
    """Señales 'no sé nada' con todas las claves del contrato."""
    senales = {clave: None for clave in CLAVES_SENALES}
    senales["url"] = url
    return senales


def _resguardo(nombre: str, funcion, respaldo, errores: dict):
    """Ejecuta una etapa; si revienta, apunta el error y sigue con el respaldo.

    Args:
        nombre: cómo se llama la etapa en el informe de errores.
        funcion: lo que hay que ejecutar (sin argumentos).
        respaldo: qué devolver si peta.
        errores: diccionario donde se apuntan los fallos.
    """
    try:
        return funcion()
    except NotImplementedError:
        errores[nombre] = "módulo todavía sin implementar"
    except Exception as e:  # noqa: BLE001 — aquí sí queremos cazarlo todo
        errores[nombre] = f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"
        log.warning("La etapa '%s' ha fallado: %s", nombre, errores[nombre])
    return respaldo


def analizar_url_suelta(url: str, formato_informe: str | None = "pdf",
                        archivo: str | None = None) -> dict:
    """Analiza UNA url ya extraída: señales → detonación → nota → informe.

    Útil para probar la cadena sin tener que fabricar un QR, y es lo que usa
    ``analizar_archivo()`` por cada URL que encuentra.

    Args:
        url: la dirección a analizar.
        formato_informe: ``"pdf"`` | ``"json"`` | ``"html"``, o None para no
            generar informe (por ejemplo al analizar un lote).

    Returns:
        dict con ``url``, ``senales``, ``sandbox``, ``scoring``, ``informe``
        y ``errores`` (vacío si ha ido todo bien).
    """
    errores: dict[str, str] = {}

    senales = _resguardo(
        "analisis_url",
        lambda: analisis_url.analizar_url(url),
        _senales_vacias(url),
        errores,
    )
    # Aunque el módulo esté a medias, garantizamos las claves del contrato.
    if not isinstance(senales, dict):
        errores["analisis_url"] = f"devolvió {type(senales).__name__}, se esperaba dict"
        senales = _senales_vacias(url)
    else:
        senales = {**_senales_vacias(url), **senales}

    if _sandbox_activo():
        detonacion = _resguardo(
            "sandbox",
            lambda: sandbox.detonar(url),
            sandbox._resultado_vacio(url, "el sandbox no llegó a ejecutarse"),
            errores,
        )
    else:
        detonacion = sandbox._resultado_vacio(url, "sandbox desactivado (QREAPER_SANDBOX=off)")

    veredicto = _resguardo(
        "scoring",
        lambda: scoring.puntuar(senales, detonacion),
        {"nota": None, "veredicto": "DESCONOCIDO", "motivos": [], "detalle": []},
        errores,
    )

    resultado = {
        "url": url,
        "senales": senales,
        "sandbox": detonacion,
        "scoring": veredicto,
        "informe": None,
        "errores": errores,
        "archivo": archivo,
    }

    if formato_informe:
        resultado["informe"] = _resguardo(
            "informe",
            lambda: informe.generar_informe(resultado, formato_informe),
            None,
            errores,
        )

    # Registro en la base de datos. Va por _resguardo a propósito: que no se
    # pueda escribir en la BD (disco lleno, permisos) no debe invalidar un
    # análisis que ya está hecho — se apunta en `errores` y se sigue.
    _resguardo("db", lambda: db.guardar(resultado), None, errores)

    return resultado


def analizar_archivo(ruta_archivo: str, formato_informe: str | None = "pdf") -> list[dict]:
    """Pipeline completo: archivo → [resultados por cada URL encontrada].

    Si el archivo no tiene QR devuelve una lista vacía. Si el que falla es el
    propio ``decode`` (módulo sin terminar, archivo corrupto...) también
    devuelve lista vacía, pero deja el motivo en el log.
    """
    errores_decode: dict[str, str] = {}
    urls = _resguardo(
        "decode",
        lambda: decode.decode(ruta_archivo),
        [],
        errores_decode,
    )

    if errores_decode:
        log.error("No se ha podido leer %s: %s", ruta_archivo, errores_decode["decode"])
        return []

    if not urls:
        log.info("No se han encontrado códigos QR con URL en %s", ruta_archivo)
        return []

    return [analizar_url_suelta(url, formato_informe, archivo=ruta_archivo)
            for url in urls]
