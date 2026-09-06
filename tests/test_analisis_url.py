# -*- coding: utf-8 -*-
"""
Modulo 2 - Pruebas del analisis estatico de URL.

Todas offline: whois y expansion de acortadores desactivados, para que el
resultado no dependa de la red ni de que un registro conteste hoy.

    pytest tests/test_analisis_url.py -q
"""
from __future__ import annotations

from qreaper.analisis_url import (
    analizar_url, decodificar_punycode, detectar_marca, distancia, esqueleto,
    es_acortador, limpiar, riesgo_tld,
)


def an(url: str) -> dict:
    """Analisis sin tocar la red."""
    return analizar_url(url, whois_activo=False, expandir_acortadores=False)


# --------------------------------------------------------------- TLD
def test_riesgo_tld():
    assert riesgo_tld("top") == "alto"
    assert riesgo_tld("zip") == "alto"
    assert riesgo_tld("info") == "medio"
    assert riesgo_tld("es") == "bajo"
    assert riesgo_tld("co.uk") == "bajo"      # se mira la ultima etiqueta
    assert riesgo_tld("") == "alto"


# --------------------------------------------------------------- Texto
def test_esqueleto_normaliza_homoglifos():
    assert esqueleto("C0RRE0S") == "correos"
    assert esqueleto("correоs") == "correos"          # o cirilica
    assert esqueleto("arnazon") == "amazon"           # rn -> m
    assert esqueleto("Iberdrolá") == "iberdrola"      # tilde aplanada
    assert esqueleto("b1nance") == "blnance"          # 1 -> l


def test_distancia():
    assert distancia("correos", "correros") == 1
    assert distancia("bbva", "bbwa") == 1
    assert distancia("abc", "abc") == 0


def test_limpiar():
    assert limpiar("  <https://correos.es/aviso>.  ") == "https://correos.es/aviso"
    assert limpiar("https://a.es/x(y)") == "https://a.es/x(y)"


def test_punycode():
    # xn--crreos-wxa = "correos" con o diacritica: en un movil se lee igual
    assert decodificar_punycode("xn--crreos-wxa.es") == "cörreos.es"


# --------------------------------------------------------------- Marcas
def test_dominio_legitimo_no_es_typosquat():
    for url in ("https://www.correos.es/es/es/particulares",
                "https://www.bbva.es/personas.html",
                "https://amazon.es/dp/B0001",
                "https://s3.eu-west-1.amazonaws.com/bucket/f.pdf"):
        r = an(url)
        assert r["es_typosquat"] is False, url
        assert r["marca_suplantada"] is None, url


def test_typosquat_tld_distinto():
    r = an("https://correos-es.top/pago")
    assert r["es_typosquat"] is True
    assert r["marca_suplantada"] == "correos"
    assert r["tld_riesgo"] == "alto"


def test_typosquat_letra_cambiada():
    assert detectar_marca("correros.es")[1] == "correos"
    assert detectar_marca("bbwa.es")[1] == "bbva"


def test_marca_en_subdominio():
    # El dominio real es pago-pendiente.top, no correos.es
    r = an("https://correos.es.pago-pendiente.top/tasa")
    assert r["es_typosquat"] is True
    assert r["marca_suplantada"] == "correos"
    assert r["detalle"]["dominio"] == "pago-pendiente.top"
    assert "subdominio" in (r["detalle"]["tecnica_typosquat"] or "")


def test_homoglifos():
    r = an("https://c0rre0s.com/envio")          # ceros por oes
    assert r["marca_suplantada"] == "correos"
    assert r["detalle"]["tecnica_typosquat"] == "homoglifos"


def test_marca_corta_delimitada():
    # 'dgt' tiene 3 letras: solo debe saltar si va delimitada...
    assert detectar_marca("dgt-multas.xyz")[1] == "dgt"
    # ...y no dentro de otra palabra.
    assert detectar_marca("widgets-online.com")[1] is None
    assert detectar_marca("groups-forum.com")[1] is None


def test_userinfo_identifica_la_marca():
    r = an("https://correos.es@dominio-malo.top/pago")
    assert r["marca_suplantada"] == "correos"
    assert "@" in (r["detalle"]["tecnica_typosquat"] or "")


# --------------------------------------------------------------- Acortadores
def test_es_acortador():
    assert es_acortador("bit.ly")
    assert es_acortador("www.tinyurl.com")
    assert not es_acortador("correos.es")
    r = an("https://bit.ly/3xYz")
    assert r["es_acortador"] is True
    assert r["url_expandida"] is None            # desactivado en las pruebas


# --------------------------------------------------------------- Deep links
def test_deep_link():
    r = an("telegram://resolve?domain=soporte_correos")
    assert r["deep_link"] == "telegram://resolve?domain=soporte_correos"
    r = an("intent://scan#Intent;scheme=zxing;package=com.malo.app;end")
    assert r["deep_link"] is not None
    assert an("https://correos.es")["deep_link"] is None


# --------------------------------------------------------------- Otras senales
def test_ip_literal():
    r = an("http://185.243.115.22/correos/pago.php")
    assert r["detalle"]["es_ip"] is True
    assert r["tld_riesgo"] == "alto"
    assert any(m["codigo"] == "host_ip" for m in r["detalle"]["motivos"])


def test_userinfo():
    r = an("https://correos.es@dominio-malo.top/pago")
    assert r["detalle"]["dominio"] == "dominio-malo.top"
    assert any(m["codigo"] == "userinfo" for m in r["detalle"]["motivos"])


def test_descarga_apk():
    r = an("https://actualiza-seur.click/app/seguimiento.apk")
    assert any(m["codigo"] == "descarga" for m in r["detalle"]["motivos"])


def test_html_no_cuenta_como_descarga():
    # Media web legitima acaba en .html: no puede ser una senal.
    r = an("https://www.bbva.es/personas.html")
    assert r["detalle"]["motivos"] == []
    assert r["detalle"]["puntuacion"] == 0


def test_punycode_no_dispara_guiones():
    # xn--crreos-wxa lleva guiones por construccion, no por sospechoso.
    codigos = {m["codigo"] for m in an("https://xn--crreos-wxa.es/aviso")["detalle"]["motivos"]}
    assert "punycode" in codigos
    assert "guiones" not in codigos


def test_redireccion_abierta():
    r = an("https://www.google.com/url?q=https://correos-pago.top/x")
    codigos = {m["codigo"] for m in r["detalle"]["motivos"]}
    assert "redireccion_abierta" in codigos


def test_redireccion_abierta_analiza_el_destino():
    r = an("https://www.google.com/url?q=https://correos-pago.top/x")
    d = r["detalle"]
    assert d["dominio"] == "google.com"            # la fachada es legitima
    assert d["url_incrustada"] == "https://correos-pago.top/x"
    assert r["es_typosquat"] is True               # la marca esta en el destino
    assert r["marca_suplantada"] == "correos"
    assert d["analisis_incrustado"]["detalle"]["analisis_incrustado"] is None


def test_puntuacion_ordena_bien():
    mala = an("https://correos.es.pago-pendiente.top/tasa-aduana")["detalle"]["puntuacion"]
    buena = an("https://www.correos.es/es/es/particulares")["detalle"]["puntuacion"]
    assert mala > 60 and buena < 20, (mala, buena)


# --------------------------------------------------------------- Contrato
def test_contrato_completo():
    """Las 8 claves de CONTRATOS.md, con sus tipos."""
    claves = {"url", "edad_dominio_dias", "tld_riesgo", "es_typosquat",
              "marca_suplantada", "es_acortador", "url_expandida", "deep_link"}
    r = an("https://correos-es.top/pago")
    assert claves.issubset(r.keys())
    assert isinstance(r["es_typosquat"], bool)
    assert isinstance(r["es_acortador"], bool)
    assert r["tld_riesgo"] in ("bajo", "medio", "alto")
    assert r["edad_dominio_dias"] is None or isinstance(r["edad_dominio_dias"], int)


def test_url_vacia_no_revienta():
    for basura in ("", "   ", "no es una url"):
        r = analizar_url(basura, whois_activo=False, expandir_acortadores=False)
        assert "tld_riesgo" in r
