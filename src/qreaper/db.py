"""
Módulo — Base de datos de análisis (SQLite) · Responsable: JuanFran

Guarda cada análisis del pipeline en una tabla `analisis` (fecha, archivo
analizado, URL detectada, veredicto, nota y motivos) y permite listarlos.

Uso:

    from qreaper import db

    db.guardar(resultado)   # resultado = dict que produce el pipeline
    db.listar()              # -> lista de análisis guardados
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

RUTA_BD = Path("qreaper.db")

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS analisis (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha     TEXT NOT NULL,
    archivo   TEXT,
    url       TEXT NOT NULL,
    veredicto TEXT,
    nota      INTEGER,
    motivos   TEXT
);
"""


def _conectar(ruta_bd: str | Path = RUTA_BD) -> sqlite3.Connection:
    conexion = sqlite3.connect(ruta_bd)
    conexion.row_factory = sqlite3.Row
    conexion.execute(_ESQUEMA)
    return conexion


def guardar(resultado: dict, ruta_bd: str | Path = RUTA_BD) -> int:
    """Guarda un análisis en la tabla `analisis`. Devuelve el id insertado.

    Espera el diccionario `resultado` del pipeline: al menos `url` y
    `scoring` ({nota, veredicto, motivos}); `archivo` es opcional (ruta del
    archivo original que se decodificó).
    """
    scoring = resultado.get("scoring", {}) or {}

    with closing(_conectar(ruta_bd)) as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO analisis (fecha, archivo, url, veredicto, nota, motivos)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                resultado.get("archivo"),
                resultado.get("url"),
                scoring.get("veredicto"),
                scoring.get("nota"),
                json.dumps(scoring.get("motivos", []), ensure_ascii=False),
            ),
        )
        conexion.commit()
        return cursor.lastrowid


def listar(ruta_bd: str | Path = RUTA_BD) -> list[dict]:
    """Devuelve todos los análisis guardados, más recientes primero."""
    with closing(_conectar(ruta_bd)) as conexion:
        filas = conexion.execute(
            "SELECT * FROM analisis ORDER BY id DESC"
        ).fetchall()
        registros = []
        for fila in filas:
            registro = dict(fila)
            registro["motivos"] = json.loads(registro.get("motivos") or "[]")
            registros.append(registro)
        return registros
