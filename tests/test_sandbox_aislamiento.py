"""
Tests de aislamiento del sandbox  ·  Jose

Aquí no se comprueba que el sandbox "funcione", sino que se NIEGUE a hacer las
cosas que no debe: abrir esquemas raros y tocar la red interna. Es la parte que
justifica que la herramienta se pueda usar sin miedo.

Los tests que necesitan Docker se saltan solos si no lo hay, para que a los
compañeros no les salga nada en rojo por no tenerlo instalado.
"""
from __future__ import annotations

import pytest

from qreaper import sandbox


# ── Esquemas que no son web ────────────────────────────────────────
@pytest.mark.parametrize(
    "url",
    [
        "file:///C:/Windows/System32/drivers/etc/hosts",
        "intent://escanear#Intent;scheme=http;end",
        "telegram://resolve?domain=algo",
        "javascript:alert(1)",
    ],
)
def test_no_detona_esquemas_que_no_son_web(url):
    res = sandbox.detonar_local(url, captura=False)

    assert res["error"], f"tendría que haberse negado a abrir {url}"
    assert "esquema" in res["error"].lower()
    assert res["hay_formulario_login"] is False


# ── Red interna (SSRF) ─────────────────────────────────────────────
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8080/admin",
        "http://localhost/panel",
        "http://192.168.1.1/",
        "http://10.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",   # metadatos de cloud
    ],
)
def test_no_detona_la_red_interna(url):
    """Un QR no puede usarnos de trampolín hacia la red de dentro."""
    motivo = sandbox._motivo_red_privada(url)

    assert motivo, f"{url} apunta a la red interna y debería bloquearse"
    assert "red interna" in motivo


def test_la_red_interna_se_puede_permitir_a_proposito(monkeypatch):
    """Para probar contra un laboratorio propio hay escotilla de escape."""
    monkeypatch.setattr(sandbox, "PERMITIR_RED_PRIVADA", True)

    assert sandbox._motivo_red_privada("http://127.0.0.1:8080/admin") is None


def test_un_dominio_publico_no_se_bloquea():
    assert sandbox._motivo_red_privada("https://b-dev.es") is None


def test_un_dominio_que_no_resuelve_no_se_bloquea_aqui():
    """Si no resuelve, que lo reporte Playwright con su mensaje, no nosotros."""
    assert sandbox._motivo_red_privada("https://esto-no-existe-jamas-12345.invalid") is None


# ── Contrato ───────────────────────────────────────────────────────
def test_el_resultado_dice_siempre_que_aislamiento_ha_usado():
    res = sandbox.detonar_local("file:///etc/passwd", captura=False)

    assert "aislamiento" in res, "el informe tiene que poder decir cómo se detonó"


# ── Motor Docker (se salta si no hay) ──────────────────────────────
falta_docker = pytest.mark.skipif(
    not sandbox.hay_imagen(),
    reason="no hay imagen de Docker: python -m qreaper.sandbox --construir-imagen",
)


@falta_docker
def test_detonar_en_docker_cumple_el_contrato():
    res = sandbox.detonar_en_docker("https://b-dev.es", captura=False)

    claves = {"url_final", "cadena_redirecciones", "screenshot_path",
              "hay_formulario_login", "error", "aislamiento"}
    assert claves <= set(res), f"faltan claves: {sorted(claves - set(res))}"
    assert res["aislamiento"] == "contenedor"
    assert res["error"] is None, f"no debería haber fallado: {res['error']}"
    assert res["url_final"].startswith("http")


@falta_docker
def test_el_contenedor_tambien_bloquea_la_red_interna():
    res = sandbox.detonar_en_docker("http://192.168.1.1/", captura=False)

    assert res["error"], "el contenedor tiene salida a internet: hay que cortarle la LAN"
    assert "red interna" in res["error"]
