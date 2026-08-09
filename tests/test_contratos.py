"""
Tests de contrato — uno por módulo.

Cada test comprueba que TU función devuelve lo que dice `CONTRATOS.md`.
Ahora mismo TODOS fallan (los módulos están vacíos). Eso es lo normal.

    ✅ Tu tarea está "Hecha" cuando tu test pasa en verde.

Ejecuta solo el tuyo:

    pytest tests/test_contratos.py -k decode      -v
    pytest tests/test_contratos.py -k analisis    -v
    pytest tests/test_contratos.py -k sandbox     -v
    pytest tests/test_contratos.py -k scoring     -v
    pytest tests/test_contratos.py -k informe     -v
"""
from pathlib import Path

import pytest

from qreaper import analisis_url, decode, informe, sandbox, scoring

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO_QR = RAIZ / "datasets" / "legitimos" / "ejemplo.png"


# ---------------------------------------------------------------- Andrés
def test_decode_devuelve_lista_de_urls():
    """decode(ruta) -> list[str] con las URLs de los QR del archivo."""
    urls = decode.decode(str(EJEMPLO_QR))

    assert isinstance(urls, list), "decode() tiene que devolver una lista"
    assert all(isinstance(u, str) for u in urls), "cada elemento es un string"
    assert len(urls) == len(set(urls)), "no puede haber URLs repetidas"
    assert any("b-dev.es" in u for u in urls), (
        "el QR de ejemplo.png apunta a b-dev.es y no lo has encontrado"
    )


# ------------------------------------------------------------------ Alex
CLAVES_SENALES = {
    "url", "edad_dominio_dias", "tld_riesgo", "es_typosquat",
    "marca_suplantada", "es_acortador", "url_expandida", "deep_link",
}


def test_analisis_url_devuelve_todas_las_senales():
    """analizar_url(url) -> dict con TODAS las claves del contrato."""
    senales = analisis_url.analizar_url("https://correos-es.top/pago")

    assert isinstance(senales, dict), "analizar_url() tiene que devolver un dict"
    faltan = CLAVES_SENALES - set(senales)
    assert not faltan, f"te faltan estas claves en el dict: {sorted(faltan)}"
    assert senales["url"] == "https://correos-es.top/pago"
    assert isinstance(senales["es_typosquat"], bool)


# ------------------------------------------------------------------ Jose
CLAVES_SANDBOX = {
    "url_final", "cadena_redirecciones", "screenshot_path",
    "hay_formulario_login", "error",
}


def test_sandbox_devuelve_evidencias():
    """detonar(url) -> dict con la URL final, redirects, screenshot y login."""
    res = sandbox.detonar("https://b-dev.es")

    assert isinstance(res, dict), "detonar() tiene que devolver un dict"
    faltan = CLAVES_SANDBOX - set(res)
    assert not faltan, f"te faltan estas claves en el dict: {sorted(faltan)}"
    assert isinstance(res["cadena_redirecciones"], list)
    assert isinstance(res["hay_formulario_login"], bool)


def test_scoring_devuelve_nota_veredicto_y_motivos():
    """puntuar(senales, sandbox) -> {nota, veredicto, motivos}."""
    senales = {
        "url": "https://correos-es.top/pago", "edad_dominio_dias": 3,
        "tld_riesgo": "alto", "es_typosquat": True, "marca_suplantada": "correos",
        "es_acortador": False, "url_expandida": None, "deep_link": None,
    }
    detonacion = {
        "url_final": "https://correos-es.top/pago", "cadena_redirecciones": [],
        "screenshot_path": None, "hay_formulario_login": True, "error": None,
    }

    res = scoring.puntuar(senales, detonacion)

    assert isinstance(res, dict), "puntuar() tiene que devolver un dict"
    assert {"nota", "veredicto", "motivos"} <= set(res)
    assert 0 <= res["nota"] <= 100, "la nota va de 0 a 100"
    assert isinstance(res["motivos"], list) and res["motivos"], (
        "hay que explicar POR QUÉ, con al menos un motivo"
    )
    assert res["veredicto"] in {"SEGURO", "SOSPECHOSO", "PELIGRO"}
    assert res["nota"] >= 70, "este caso es phishing de libro, debería puntuar alto"


# -------------------------------------------------------------- JuanFran
@pytest.mark.parametrize("formato", ["json", "html", "pdf"])
def test_informe_genera_el_archivo(formato, tmp_path, monkeypatch):
    """generar_informe(resultado, formato) -> ruta de un archivo que existe."""
    monkeypatch.chdir(tmp_path)
    resultado = {
        "url": "https://correos-es.top/pago",
        "senales": {"edad_dominio_dias": 3, "es_typosquat": True},
        "sandbox": {"hay_formulario_login": True, "screenshot_path": None},
        "scoring": {"nota": 87, "veredicto": "PELIGRO", "motivos": ["dominio nuevo"]},
    }

    ruta = informe.generar_informe(resultado, formato)

    assert isinstance(ruta, str), "generar_informe() devuelve la RUTA (string)"
    assert Path(ruta).exists(), f"el archivo {ruta} no se ha creado"
    assert Path(ruta).suffix.lstrip(".") == formato
