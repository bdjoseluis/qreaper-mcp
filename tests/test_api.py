"""
Pruebas de la capa API REST (parte de Jose).

No dependen de Docker ni de red: monkeypatchean el pipeline y la BD para
comprobar que los endpoints enrutan bien, validan la entrada y serializan la
salida. La lógica de análisis ya tiene sus propias baterías por módulo.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from qreaper import api  # noqa: E402


@pytest.fixture
def cliente(monkeypatch):
    """TestClient con el pipeline y la BD simulados."""

    def _fake_url_suelta(url, formato_informe=None, archivo=None):
        return {
            "url": url,
            "senales": {"url": url},
            "sandbox": {"url_final": url},
            "scoring": {"nota": 10, "veredicto": "PELIGRO", "motivos": ["typosquat"]},
            "informe": None,
            "errores": {},
            "archivo": archivo,
        }

    def _fake_archivo(ruta, formato_informe=None):
        return [_fake_url_suelta("https://malo.top/x", archivo=ruta)]

    def _fake_listar(*a, **k):
        return [
            {"id": 2, "url": "https://malo.top", "veredicto": "PELIGRO", "nota": 5, "motivos": []},
            {"id": 1, "url": "https://banco.es", "veredicto": "SEGURO", "nota": 95, "motivos": []},
        ]

    monkeypatch.setattr(api.pipeline, "analizar_url_suelta", _fake_url_suelta)
    monkeypatch.setattr(api.pipeline, "analizar_archivo", _fake_archivo)
    monkeypatch.setattr(api.db, "listar", _fake_listar)
    return TestClient(api.app)


def test_salud(cliente):
    r = cliente.get("/salud")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"


def test_raiz_lista_endpoints(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert "POST /analizar/url" in r.json()["endpoints"]


def test_analizar_url_ok(cliente):
    r = cliente.post("/analizar/url", json={"url": "https://correos-es.top/pago"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["scoring"]["veredicto"] == "PELIGRO"
    assert cuerpo["url"] == "https://correos-es.top/pago"


def test_analizar_url_vacia_da_422(cliente):
    r = cliente.post("/analizar/url", json={"url": "   "})
    assert r.status_code == 422


def test_analizar_url_formato_invalido_da_422(cliente):
    r = cliente.post("/analizar/url", json={"url": "https://x.es", "formato": "docx"})
    assert r.status_code == 422


def test_analizar_archivo_ok(cliente):
    r = cliente.post(
        "/analizar/archivo",
        files={"archivo": ("qr.png", b"\x89PNG fake bytes", "image/png")},
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["urls_encontradas"] == 1
    assert cuerpo["resultados"][0]["scoring"]["veredicto"] == "PELIGRO"


def test_analizar_archivo_vacio_da_422(cliente):
    r = cliente.post(
        "/analizar/archivo",
        files={"archivo": ("vacio.png", b"", "image/png")},
    )
    assert r.status_code == 422


def test_historial_lista(cliente):
    r = cliente.get("/historial")
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_historial_filtra_por_veredicto(cliente):
    r = cliente.get("/historial", params={"veredicto": "seguro"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == 1
    assert cuerpo["analisis"][0]["veredicto"] == "SEGURO"


def test_historial_por_id_ok(cliente):
    r = cliente.get("/historial/1")
    assert r.status_code == 200
    assert r.json()["url"] == "https://banco.es"


def test_historial_por_id_inexistente_da_404(cliente):
    r = cliente.get("/historial/999")
    assert r.status_code == 404
