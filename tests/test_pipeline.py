"""
Tests del orquestador  ·  Jose

Lo que se comprueba aquí es la RESISTENCIA: mientras los compañeros terminan
sus módulos, el pipeline tiene que seguir dando un resultado útil en vez de
reventar. Estos tests no tocan la red: el sandbox va siempre mockeado.
"""
from __future__ import annotations

import pytest

from qreaper import pipeline, sandbox

SANDBOX_FALSO = {
    "url_final": "https://correos-es.top/pago",
    "cadena_redirecciones": ["https://correos-es.top/pago"],
    "screenshot_path": None,
    "hay_formulario_login": True,
    "error": None,
    "aislamiento": "contenedor",
}


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Ningún test de este archivo abre el navegador de verdad."""
    monkeypatch.setattr(sandbox, "detonar", lambda url, **kw: dict(SANDBOX_FALSO, url_final=url))


# ── El pipeline aguanta con módulos a medio hacer ───────────────────
def test_pipeline_no_revienta_con_modulos_sin_implementar():
    """analisis_url e informe lanzan NotImplementedError: no debe propagarse."""
    res = pipeline.analizar_url_suelta("https://correos-es.top/pago", formato_informe="json")

    assert isinstance(res, dict)
    assert res["url"] == "https://correos-es.top/pago"
    assert "analisis_url" in res["errores"], "el fallo de Alex tiene que quedar apuntado"
    assert "informe" in res["errores"], "el fallo de JuanFran tiene que quedar apuntado"


def test_pipeline_sigue_puntuando_aunque_falte_analisis_url():
    """Con solo las señales dinámicas, scoring tiene que dar nota igualmente."""
    res = pipeline.analizar_url_suelta("https://correos-es.top/pago", formato_informe=None)

    assert res["scoring"]["nota"] is not None
    assert res["scoring"]["veredicto"] in {"SEGURO", "SOSPECHOSO", "PELIGRO"}
    assert res["scoring"]["motivos"], "aunque falte un módulo hay que explicar la nota"


def test_senales_siempre_tienen_las_claves_del_contrato():
    """Aunque analisis_url falle, el informe recibe el dict completo."""
    res = pipeline.analizar_url_suelta("https://correos-es.top/pago", formato_informe=None)

    faltan = set(pipeline.CLAVES_SENALES) - set(res["senales"])
    assert not faltan, f"faltan claves en senales: {sorted(faltan)}"
    assert res["senales"]["url"] == "https://correos-es.top/pago"


def test_pipeline_completa_las_claves_que_falten(monkeypatch):
    """Si alguien devuelve un dict incompleto, se rellena en vez de petar."""
    from qreaper import analisis_url

    monkeypatch.setattr(analisis_url, "analizar_url", lambda url: {"url": url, "es_typosquat": True})
    res = pipeline.analizar_url_suelta("https://correos-es.top/pago", formato_informe=None)

    assert res["senales"]["es_typosquat"] is True
    assert res["senales"]["tld_riesgo"] is None
    assert not res["errores"].get("analisis_url")


def test_pipeline_apunta_error_si_devuelven_algo_que_no_es_dict(monkeypatch):
    from qreaper import analisis_url

    monkeypatch.setattr(analisis_url, "analizar_url", lambda url: ["esto", "no", "vale"])
    res = pipeline.analizar_url_suelta("https://correos-es.top/pago", formato_informe=None)

    assert "analisis_url" in res["errores"]
    assert res["senales"]["url"] == "https://correos-es.top/pago"


# ── analizar_archivo ────────────────────────────────────────────────
def test_analizar_archivo_devuelve_lista_vacia_si_no_hay_qr(monkeypatch):
    from qreaper import decode

    monkeypatch.setattr(decode, "decode", lambda ruta: [])
    assert pipeline.analizar_archivo("loquesea.png", formato_informe=None) == []


def test_analizar_archivo_no_revienta_si_decode_falla(monkeypatch):
    from qreaper import decode

    def explota(ruta):
        raise FileNotFoundError("no existe")

    monkeypatch.setattr(decode, "decode", explota)
    assert pipeline.analizar_archivo("noexiste.png", formato_informe=None) == []


def test_analizar_archivo_un_resultado_por_url(monkeypatch):
    from qreaper import decode

    monkeypatch.setattr(
        decode, "decode",
        lambda ruta: ["https://uno.example", "https://dos.example"],
    )
    res = pipeline.analizar_archivo("correo.eml", formato_informe=None)

    assert len(res) == 2
    assert [r["url"] for r in res] == ["https://uno.example", "https://dos.example"]
