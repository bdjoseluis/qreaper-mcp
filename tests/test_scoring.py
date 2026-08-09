"""
Tests del motor de scoring (Jose).

Estos tests fijan la CALIBRACIÓN del detector: si alguien toca los pesos de
`scoring.py` y rompe uno de estos casos, es que ha desajustado el detector.

Los casos están sacados de campañas de quishing reales (facturas falsas de
Correos, multas de la DGT, "tu paquete está retenido"...).
"""
from qreaper import scoring

SANDBOX_LIMPIO = {
    "url_final": None, "cadena_redirecciones": [], "screenshot_path": None,
    "hay_formulario_login": False, "error": None,
}


def _senales(**kwargs) -> dict:
    base = {
        "url": "https://ejemplo.com/", "edad_dominio_dias": 3000,
        "tld_riesgo": "bajo", "es_typosquat": False, "marca_suplantada": None,
        "es_acortador": False, "url_expandida": None, "deep_link": None,
    }
    base.update(kwargs)
    return base


def test_web_legitima_de_toda_la_vida_es_segura():
    res = scoring.puntuar(_senales(), SANDBOX_LIMPIO)
    assert res["veredicto"] == "SEGURO"
    assert res["nota"] == 0
    assert res["motivos"], "aunque sea segura, hay que decir algo al usuario"


def test_banco_legitimo_pidiendo_login_no_es_phishing():
    """Pedir contraseña NO es delito: tu banco lo hace. No debe dar PELIGRO."""
    sandbox = {**SANDBOX_LIMPIO, "hay_formulario_login": True,
               "url_final": "https://ejemplo.com/"}
    res = scoring.puntuar(_senales(), sandbox)
    assert res["veredicto"] == "SEGURO", "falso positivo: un login legítimo alarma al usuario"


def test_quishing_clasico_de_correos_da_peligro():
    """Dominio de 3 días + imita a Correos + pide credenciales."""
    senales = _senales(
        url="https://correos-es.top/pago", edad_dominio_dias=3,
        tld_riesgo="alto", es_typosquat=True, marca_suplantada="correos",
    )
    sandbox = {**SANDBOX_LIMPIO, "hay_formulario_login": True,
               "url_final": "https://correos-es.top/pago"}
    res = scoring.puntuar(senales, sandbox)

    assert res["veredicto"] == "PELIGRO"
    assert res["nota"] >= 90
    assert any("correos" in m.lower() for m in res["motivos"])


def test_acortador_que_acaba_en_otro_dominio_es_sospechoso():
    senales = _senales(
        url="https://bit.ly/abc123", es_acortador=True,
        url_expandida="https://pagar-multa.xyz/dgt", edad_dominio_dias=None,
    )
    sandbox = {**SANDBOX_LIMPIO, "url_final": "https://pagar-multa.xyz/dgt",
               "cadena_redirecciones": ["https://bit.ly/abc123",
                                        "https://pagar-multa.xyz/dgt"]}
    res = scoring.puntuar(senales, sandbox)
    assert res["veredicto"] in {"SOSPECHOSO", "PELIGRO"}


def test_deep_link_a_telegram_puntua_alto():
    senales = _senales(deep_link="telegram://resolve?domain=soporte_bbva")
    res = scoring.puntuar(senales, SANDBOX_LIMPIO)
    assert res["nota"] >= scoring.PUNTOS_DEEP_LINK


def test_si_el_sandbox_falla_se_avisa_y_no_se_dice_que_es_seguro_sin_mas():
    senales = _senales(edad_dominio_dias=20, tld_riesgo="alto")
    sandbox = {**SANDBOX_LIMPIO, "error": "Timeout de 20s"}
    res = scoring.puntuar(senales, sandbox)
    assert any("no se ha podido abrir" in m.lower() for m in res["motivos"])
    assert res["veredicto"] != "SEGURO", "no podemos dar por buena una web que no hemos visto"


def test_la_nota_nunca_se_pasa_de_100():
    senales = _senales(
        url="https://correos-es.top/x", edad_dominio_dias=1, tld_riesgo="alto",
        es_typosquat=True, marca_suplantada="correos", es_acortador=True,
        deep_link="intent://x",
    )
    sandbox = {**SANDBOX_LIMPIO, "hay_formulario_login": True,
               "url_final": "https://otro-dominio.xyz/x",
               "cadena_redirecciones": ["a", "b", "c", "d"]}
    res = scoring.puntuar(senales, sandbox)
    assert res["nota"] == 100


def test_cada_motivo_viene_con_sus_puntos_para_el_informe():
    """El informe de JuanFran necesita el desglose, no solo la nota."""
    senales = _senales(edad_dominio_dias=2, tld_riesgo="alto")
    res = scoring.puntuar(senales, SANDBOX_LIMPIO)
    assert res["detalle"], "falta el desglose"
    assert {"senal", "puntos", "motivo"} == set(res["detalle"][0])
    assert sum(d["puntos"] for d in res["detalle"]) == res["nota"]
