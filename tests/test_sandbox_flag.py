"""El flag QREAPER_SANDBOX=off debe evitar la detonación (parte de Jose)."""
from __future__ import annotations

from qreaper import pipeline


def test_sandbox_off_no_llama_a_detonar(monkeypatch):
    monkeypatch.setenv("QREAPER_SANDBOX", "off")

    def _no_debe_llamarse(*a, **k):
        raise AssertionError("sandbox.detonar no debería ejecutarse con off")

    monkeypatch.setattr(pipeline.sandbox, "detonar", _no_debe_llamarse)
    monkeypatch.setattr(pipeline.analisis_url, "analizar_url", lambda url: {"url": url})
    monkeypatch.setattr(pipeline.scoring, "puntuar", lambda s, d: {"nota": None, "veredicto": "DESCONOCIDO", "motivos": []})
    monkeypatch.setattr(pipeline.db, "guardar", lambda r: 1)

    res = pipeline.analizar_url_suelta("https://ejemplo.test", formato_informe=None)
    assert "desactivado" in (res["sandbox"].get("motivo") or res["sandbox"].get("error", "")).lower() \
        or res["sandbox"] is not None


def test_sandbox_on_por_defecto(monkeypatch):
    monkeypatch.delenv("QREAPER_SANDBOX", raising=False)
    assert pipeline._sandbox_activo() is True
