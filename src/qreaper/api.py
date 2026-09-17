"""
Módulo — API REST (FastAPI)  ·  Responsable: Jose (integración)

Capa HTTP sobre el pipeline. No implementa lógica de análisis: expone el
mismo motor que usa el CLI a través de varios endpoints que hacen cosas
distintas (analizar una URL, analizar un archivo subido, consultar el
historial guardado en la base de datos).

Levantar en local:

    uvicorn qreaper.api:app --reload
    # o bien:  qreaper-api          (script declarado en pyproject)

Docs interactivas automáticas en  http://localhost:8000/docs
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

MAX_ARCHIVO_BYTES = 10 * 1024 * 1024  # 10 MB

# Extensiones que acepta decode.py; nada más pasa al pipeline.
_EXTENSIONES_PERMITIDAS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".pdf", ".eml",
}

# Primeros bytes esperados según extensión (magic bytes).
_MAGIC: dict[str, bytes] = {
    ".png":  b"\x89PNG",
    ".jpg":  b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".bmp":  b"BM",
    ".gif":  b"GIF8",
    ".tiff": b"II",   # big-endian también empieza con MM; se comprueba aparte
    ".tif":  b"II",
    ".pdf":  b"%PDF",
}


def _valida_archivo(contenido: bytes, sufijo: str) -> None:
    firma = _MAGIC.get(sufijo)
    if not firma:
        return  # .eml es texto plano, sin firma binaria fiable
    es_tiff_be = sufijo in (".tiff", ".tif") and contenido.startswith(b"MM")
    if not es_tiff_be and not contenido.startswith(firma):
        raise HTTPException(
            status_code=422,
            detail=f"El contenido no coincide con la extensión '{sufijo}'.",
        )

from . import db, pipeline

log = logging.getLogger("qreaper.api")

VERSION = "0.1.0"

app = FastAPI(
    title="QReaper API",
    version=VERSION,
    description=(
        "Analizador anti-quishing. Extrae URLs de códigos QR (imagen, PDF, "
        "email), las detona en un sandbox aislado y devuelve un veredicto de "
        "riesgo. Cada análisis se registra en la base de datos."
    ),
)

# Formatos de informe válidos (mismos que el CLI). `None` = no generar archivo.
_FORMATOS = {"pdf", "html", "json"}


# ---------------------------------------------------------------------------
# Modelos de entrada/salida
# ---------------------------------------------------------------------------

class AnalisisUrlPeticion(BaseModel):
    """Cuerpo de POST /analizar/url."""

    url: str = Field(..., description="URL a analizar.", examples=["https://correos-es.top/pago"])
    formato: str | None = Field(
        default=None,
        description="Formato del informe a generar en disco: pdf|html|json. "
        "Omitir para no generar archivo (respuesta JSON directa).",
    )


def _valida_formato(formato: str | None) -> str | None:
    if formato is None:
        return None
    formato = formato.lower()
    if formato not in _FORMATOS:
        raise HTTPException(
            status_code=422,
            detail=f"formato inválido '{formato}'. Válidos: {sorted(_FORMATOS)} o null.",
        )
    return formato


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/app", tags=["meta"], include_in_schema=False)
def web_app():
    """Web mínima de respaldo (una sola página que consume esta misma API)."""
    from . import web

    return web.pagina_html()


@app.get("/", tags=["meta"])
def raiz() -> dict:
    """Información básica de la API y enlaces útiles."""
    return {
        "servicio": "QReaper API",
        "version": VERSION,
        "docs": "/docs",
        "web": "/app",
        "endpoints": [
            "POST /analizar/url",
            "POST /analizar/archivo",
            "GET /historial",
            "GET /historial/{id}",
            "GET /salud",
        ],
    }


@app.get("/salud", tags=["meta"])
def salud() -> dict:
    """Comprobación de vida (para balanceadores / monitorización)."""
    return {"estado": "ok", "version": VERSION}


@app.post("/analizar/url", tags=["analisis"])
def analizar_url(peticion: AnalisisUrlPeticion) -> dict:
    """Analiza UNA URL directa y devuelve el resultado completo del pipeline."""
    formato = _valida_formato(peticion.formato)
    url = peticion.url.strip()
    if not url:
        raise HTTPException(status_code=422, detail="La URL no puede estar vacía.")
    log.info("Analizando URL: %s", url)
    return pipeline.analizar_url_suelta(url, formato)


@app.post("/analizar/archivo", tags=["analisis"])
async def analizar_archivo(
    archivo: UploadFile = File(..., description="Imagen, PDF o email (.eml) con un QR."),
    formato: str | None = Query(default=None, description="pdf|html|json o vacío."),
) -> dict:
    """Sube un archivo (imagen/PDF/.eml), extrae los QR y analiza cada URL."""
    formato = _valida_formato(formato)

    # Guardamos el subido en un temporal conservando la extensión: decode elige
    # el lector (imagen/pdf/eml) según ella.
    sufijo = Path(archivo.filename or "").suffix.lower() or ".bin"
    if sufijo not in _EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=415,
            detail=f"Extensión '{sufijo}' no admitida. Usa: {', '.join(sorted(_EXTENSIONES_PERMITIDAS))}.",
        )

    contenido = await archivo.read(MAX_ARCHIVO_BYTES + 1)
    if len(contenido) > MAX_ARCHIVO_BYTES:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 10 MB).")
    if not contenido:
        raise HTTPException(status_code=422, detail="El archivo está vacío.")
    _valida_archivo(contenido, sufijo)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=sufijo)
    try:
        tmp.write(contenido)
        tmp.close()
        resultados = pipeline.analizar_archivo(tmp.name, formato)
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    return {
        "archivo": archivo.filename,
        "urls_encontradas": len(resultados),
        "resultados": resultados,
    }


@app.get("/historial", tags=["historial"])
def historial(
    limite: int = Query(default=50, ge=1, le=500, description="Máximo de registros."),
    veredicto: str | None = Query(
        default=None,
        description="Filtra por veredicto: PELIGRO|SOSPECHOSO|SEGURO|DESCONOCIDO.",
    ),
) -> dict:
    """Lista los análisis guardados en la base de datos, más recientes primero."""
    registros = db.listar()
    if veredicto:
        v = veredicto.upper()
        registros = [r for r in registros if (r.get("veredicto") or "").upper() == v]
    registros = registros[:limite]
    return {"total": len(registros), "analisis": registros}


@app.get("/historial/{analisis_id}", tags=["historial"])
def historial_por_id(analisis_id: int) -> dict:
    """Devuelve un análisis concreto por su id."""
    for r in db.listar():
        if r.get("id") == analisis_id:
            return r
    raise HTTPException(status_code=404, detail=f"No existe el análisis {analisis_id}.")


def main() -> None:
    """Punto de entrada del script `qreaper-api`: arranca uvicorn."""
    import uvicorn

    uvicorn.run("qreaper.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
