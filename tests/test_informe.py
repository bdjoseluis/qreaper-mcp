"""
Tests del módulo informe  ·  JuanFran

Los tres del contrato (``test_contratos.py``) solo comprueban que el archivo
se crea. Aquí se comprueba lo que de verdad puede romperse en producción: que
el informe salga igual aunque los demás módulos vengan a medias, y que no se
invente datos que no tiene.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from qreaper import informe

RESULTADO_COMPLETO = {
    "url": "https://correos-es.top/pago",
    "senales": {
        "url": "https://correos-es.top/pago",
        "edad_dominio_dias": 3,
        "tld_riesgo": "alto",
        "es_typosquat": True,
        "marca_suplantada": "Correos",
        "es_acortador": False,
        "url_expandida": None,
        "deep_link": None,
    },
    "sandbox": {
        "url_final": "https://correos-es.top/pago",
        "cadena_redirecciones": ["https://correos-es.top/pago"],
        "screenshot_path": None,
        "hay_formulario_login": True,
        "error": None,
        "aislamiento": "contenedor",
    },
    "scoring": {
        "nota": 87,
        "veredicto": "PELIGRO",
        "motivos": ["El dominio se registró hace 3 días"],
        "detalle": [{"senal": "edad_dominio", "puntos": 25, "motivo": "Dominio muy nuevo"}],
    },
    "informe": None,
    "errores": {},
}


@pytest.fixture(autouse=True)
def en_carpeta_temporal(tmp_path, monkeypatch):
    """Ningún test escribe informes dentro del repo."""
    monkeypatch.chdir(tmp_path)


# ── Contrato de la función ──────────────────────────────────────────
def test_formato_desconocido_avisa_claramente():
    with pytest.raises(ValueError, match="no soportado"):
        informe.generar_informe(RESULTADO_COMPLETO, "docx")


@pytest.mark.parametrize("entrada", ["PDF", ".pdf", " pdf "])
def test_el_formato_no_distingue_mayusculas_ni_espacios(entrada):
    """Si Ismael pasa lo que escribe el usuario en la CLI, no debe petar."""
    ruta = informe.generar_informe(RESULTADO_COMPLETO, entrada)
    assert Path(ruta).suffix == ".pdf"


def test_destino_explicito_manda(tmp_path):
    destino = tmp_path / "informes" / "caso-01.html"
    ruta = informe.generar_informe(RESULTADO_COMPLETO, "html", destino=str(destino))

    assert Path(ruta) == destino
    assert destino.exists(), "la carpeta de destino debe crearse sola"


def test_destino_sin_extension_recibe_la_del_formato(tmp_path):
    ruta = informe.generar_informe(
        RESULTADO_COMPLETO, "json", destino=str(tmp_path / "caso-02")
    )
    assert Path(ruta).suffix == ".json"


def test_el_nombre_por_defecto_lleva_el_dominio():
    ruta = informe.generar_informe(RESULTADO_COMPLETO, "json")
    assert "correos-es.top" in ruta


# ── Resistencia: los otros módulos van a medias ─────────────────────
@pytest.mark.parametrize("formato", ["json", "html", "pdf"])
def test_se_genera_aunque_el_resultado_venga_vacio(formato):
    """Caso real: falla todo menos el pipeline. Tiene que salir informe igual."""
    ruta = informe.generar_informe({}, formato)
    assert Path(ruta).exists()


@pytest.mark.parametrize("formato", ["json", "html", "pdf"])
def test_se_genera_con_las_claves_a_None(formato):
    """Lo que deja el pipeline cuando analisis_url y sandbox no responden."""
    a_medias = {
        "url": "https://ejemplo.test/qr",
        "senales": {"url": "https://ejemplo.test/qr", "edad_dominio_dias": None},
        "sandbox": {"screenshot_path": None, "error": "el sandbox no llegó a ejecutarse"},
        "scoring": {"nota": None, "veredicto": "DESCONOCIDO", "motivos": [], "detalle": []},
        "errores": {"analisis_url": "módulo todavía sin implementar"},
    }
    ruta = informe.generar_informe(a_medias, formato)
    assert Path(ruta).exists()


def test_sin_nota_no_se_inventa_un_cero():
    """Un 0/100 se leería como 'seguro'. Sin datos es sin datos."""
    sin_nota = {"url": "https://ejemplo.test", "scoring": {"nota": None, "veredicto": "DESCONOCIDO"}}
    contenido = Path(informe.generar_informe(sin_nota, "html")).read_text(encoding="utf-8")

    assert "sin datos" in contenido
    assert "0/100" not in contenido


def test_veredicto_raro_cae_en_desconocido():
    raro = {"url": "https://ejemplo.test", "scoring": {"veredicto": "PLATANO", "nota": 10}}
    contenido = Path(informe.generar_informe(raro, "html")).read_text(encoding="utf-8")

    assert "DESCONOCIDO" in contenido
    assert "PLATANO" not in contenido


def test_las_senales_que_no_llegan_no_aparecen():
    """No decir 'Marca suplantada: no' cuando en realidad no se ha mirado."""
    contenido = Path(informe.generar_informe(RESULTADO_COMPLETO, "html")).read_text(
        encoding="utf-8"
    )
    assert "Marca suplantada" in contenido  # esta sí viene
    assert "deep link" not in contenido.lower()  # esta viene a None


def test_los_errores_del_pipeline_salen_en_el_informe():
    con_fallos = dict(RESULTADO_COMPLETO, errores={"sandbox": "Docker no está arrancado"})
    contenido = Path(informe.generar_informe(con_fallos, "html")).read_text(encoding="utf-8")

    assert "Docker no está arrancado" in contenido


# ── Formatos ────────────────────────────────────────────────────────
def test_json_conserva_el_analisis_entero_y_es_valido():
    datos = json.loads(
        Path(informe.generar_informe(RESULTADO_COMPLETO, "json")).read_text(encoding="utf-8")
    )
    assert datos["veredicto"] == "PELIGRO"
    assert datos["analisis"]["senales"]["marca_suplantada"] == "Correos"
    assert datos["recomendacion"]


def test_json_no_revienta_con_objetos_raros():
    """whois devuelve datetimes: no pueden tumbar el informe."""
    from datetime import datetime

    con_fecha = dict(RESULTADO_COMPLETO)
    con_fecha["senales"] = dict(RESULTADO_COMPLETO["senales"], creado=datetime(2026, 8, 1))

    ruta = informe.generar_informe(con_fecha, "json")
    assert "2026-08-01" in Path(ruta).read_text(encoding="utf-8")


def test_html_escapa_lo_que_venga_de_fuera():
    """La URL la controla el atacante: no puede inyectar HTML en el informe."""
    malicioso = dict(RESULTADO_COMPLETO, url="https://x.test/<script>alert(1)</script>")
    contenido = Path(informe.generar_informe(malicioso, "html")).read_text(encoding="utf-8")

    assert "<script>alert(1)</script>" not in contenido
    assert "&lt;script&gt;" in contenido


def test_html_incrusta_la_captura(tmp_path):
    """El HTML tiene que poder enviarse suelto, sin la carpeta de capturas."""
    captura = tmp_path / "captura.png"
    # PNG de 1x1 válido, para no depender de Pillow en los tests.
    captura.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6300010000050001"
        "0d0a2db40000000049454e44ae426082"
    ))
    con_captura = dict(RESULTADO_COMPLETO)
    con_captura["sandbox"] = dict(
        RESULTADO_COMPLETO["sandbox"], screenshot_path=str(captura)
    )

    contenido = Path(informe.generar_informe(con_captura, "html")).read_text(encoding="utf-8")
    assert "data:image/png;base64," in contenido


def test_una_captura_que_ya_no_esta_no_rompe_el_informe():
    perdida = dict(RESULTADO_COMPLETO)
    perdida["sandbox"] = dict(
        RESULTADO_COMPLETO["sandbox"], screenshot_path="no_existe_esta_captura.png"
    )
    assert Path(informe.generar_informe(perdida, "html")).exists()
    assert Path(informe.generar_informe(perdida, "pdf")).exists()


def test_el_pdf_es_un_pdf_de_verdad():
    ruta = informe.generar_informe(RESULTADO_COMPLETO, "pdf")
    with open(ruta, "rb") as f:
        assert f.read(5) == b"%PDF-", "el archivo tiene que ser un PDF, no texto con otra extensión"
