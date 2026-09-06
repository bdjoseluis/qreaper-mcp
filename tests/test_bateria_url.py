# -*- coding: utf-8 -*-
"""
Modulo 2 - Banco de pruebas contra el dataset del repo.

Lee datasets/legitimos/urls.txt y datasets/maliciosos/urls.txt y comprueba
que el analisis estatico separa unas de otras. Es la red de seguridad al
tocar las listas de datos_url.py o los pesos de las senales: si una marca
nueva mete falsos positivos, aqui salta.

    pytest tests/test_bateria_url.py -q
    pytest tests/test_bateria_url.py -q -s --tb=no      # ver la tabla
"""
from __future__ import annotations

from pathlib import Path

import pytest

from qreaper.analisis_url import analizar_url

RAIZ = Path(__file__).resolve().parents[1]
UMBRAL = 45          # a partir de aqui se considera detectada


def cargar(nombre: str) -> list[str]:
    fichero = RAIZ / "datasets" / nombre / "urls.txt"
    if not fichero.exists():
        pytest.skip(f"falta {fichero}")
    return [ln.strip() for ln in fichero.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def puntuar(url: str) -> dict:
    """Siempre offline: el resultado tiene que ser reproducible."""
    return analizar_url(url, whois_activo=False, expandir_acortadores=False)


@pytest.mark.parametrize("url", cargar("legitimos"))
def test_legitimas_no_dan_falso_positivo(url):
    d = puntuar(url)["detalle"]
    assert d["puntuacion"] < UMBRAL, (
        f"FALSO POSITIVO en {url}: {d['puntuacion']}/100 por "
        + "; ".join(m["codigo"] for m in d["motivos"]))


@pytest.mark.parametrize("url", cargar("maliciosos"))
def test_maliciosas_se_detectan(url):
    d = puntuar(url)["detalle"]
    assert d["puntuacion"] >= UMBRAL, (
        f"FALSO NEGATIVO en {url}: solo {d['puntuacion']}/100")


def test_resumen(capsys):
    """No comprueba nada nuevo: imprime la tabla para la memoria."""
    filas = []
    for grupo, maliciosa in (("legitimos", False), ("maliciosos", True)):
        for url in cargar(grupo):
            r = puntuar(url)
            d = r["detalle"]
            filas.append((url, d["puntuacion"], d["nivel"],
                          r["marca_suplantada"], maliciosa,
                          (d["puntuacion"] >= UMBRAL) == maliciosa))
    with capsys.disabled():
        print(f"\n{'URL':<58} {'punt':>4} {'nivel':<8} marca")
        print("-" * 90)
        for url, punt, nivel, marca, _, ok in filas:
            print(f"{' ' if ok else '!'}{url[:57]:<57} {punt:>4} "
                  f"{nivel:<8} {marca or '-'}")
        aciertos = sum(1 for f in filas if f[5])
        print("-" * 90)
        print(f"Aciertos: {aciertos}/{len(filas)}  (umbral {UMBRAL}/100)")
    assert all(f[5] for f in filas)
