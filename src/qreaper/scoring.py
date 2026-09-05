"""
Módulo 4 — Scoring  ·  Responsable: Jose

Combina las señales ESTÁTICAS (análisis de URL, sin abrirla) con las DINÁMICAS
(lo que ha pasado al detonarla en el sandbox) y las convierte en una nota de
riesgo 0-100, un veredicto y — lo más importante para el usuario — los MOTIVOS
en cristiano.

Filosofía: nada de cajas negras. Cada punto que suma la nota tiene un motivo
explicable. Un analista tiene que poder discutir el resultado.
"""
from __future__ import annotations

from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Tabla de pesos. Tocar SOLO aquí para recalibrar el detector.
# Cada entrada: (puntos, motivo que se le enseña al usuario)
# ---------------------------------------------------------------------------

#: A partir de esta nota, veredicto PELIGRO.
UMBRAL_PELIGRO = 70
#: A partir de esta nota, veredicto SOSPECHOSO.
UMBRAL_SOSPECHOSO = 35

#: Edad del dominio: (días máximos, puntos, motivo)
PESOS_EDAD_DOMINIO = [
    (7, 25, "El dominio se registró hace menos de una semana"),
    (30, 18, "El dominio tiene menos de un mes de vida"),
    (90, 10, "El dominio tiene menos de tres meses"),
    (365, 4, "El dominio tiene menos de un año"),
]
#: Si no se pudo averiguar la edad (whois sin datos): sospecha leve.
PUNTOS_EDAD_DESCONOCIDA = 5

#: Riesgo del TLD (.zip, .top, .xyz... son baratos y muy usados en phishing)
PESOS_TLD = {
    "alto": (15, "La extensión del dominio es de las más usadas para fraude"),
    "medio": (8, "La extensión del dominio es poco habitual"),
    "bajo": (0, ""),
}

PUNTOS_TYPOSQUAT = 25
PUNTOS_ACORTADOR = 10
PUNTOS_DEEP_LINK = 20
PUNTOS_FORMULARIO_LOGIN = 20
PUNTOS_CADENA_REDIRECCIONES = 12   # 3 o más saltos
PUNTOS_ALGUNA_REDIRECCION = 5      # 1 o 2 saltos
PUNTOS_CAMBIO_DE_DOMINIO = 10      # acaba en un dominio distinto del inicial

#: Combinaciones que juntas son mucho peor que por separado.
PUNTOS_COMBO_TYPOSQUAT_LOGIN = 10
PUNTOS_COMBO_DOMINIO_NUEVO_LOGIN = 8
PUNTOS_COMBO_ACORTADOR_OTRO_DOMINIO = 8

NOTA_MAXIMA = 100


def _dominio(url: str | None) -> str:
    """Devuelve el host de una URL, en minúsculas y sin 'www.'."""
    if not url:
        return ""
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _puntos_por_edad(dias) -> tuple[int, str]:
    if dias is None:
        return PUNTOS_EDAD_DESCONOCIDA, "No se ha podido comprobar la antigüedad del dominio"
    for tope, puntos, motivo in PESOS_EDAD_DOMINIO:
        if dias < tope:
            return puntos, f"{motivo} (registrado hace {dias} días)"
    return 0, ""


def puntuar(senales_url: dict, resultado_sandbox: dict) -> dict:
    """Combina todas las señales en una nota 0-100 y un veredicto.

    Args:
        senales_url: lo que devuelve ``analisis_url.analizar_url()``.
        resultado_sandbox: lo que devuelve ``sandbox.detonar()``.

    Returns:
        dict con:
          - ``nota``: 0-100 (100 = certeza de fraude)
          - ``veredicto``: ``"SEGURO"`` | ``"SOSPECHOSO"`` | ``"PELIGRO"``
          - ``motivos``: lista de explicaciones en lenguaje llano
          - ``detalle``: lista de ``{"señal", "puntos", "motivo"}`` para el informe
    """
    senales_url = senales_url or {}
    resultado_sandbox = resultado_sandbox or {}

    detalle: list[dict] = []

    def anota(senal: str, puntos: int, motivo: str) -> None:
        if puntos > 0 and motivo:
            detalle.append({"senal": senal, "puntos": puntos, "motivo": motivo})

    # ---------------------------------------------------------- estáticas
    puntos, motivo = _puntos_por_edad(senales_url.get("edad_dominio_dias"))
    anota("edad_dominio", puntos, motivo)

    riesgo_tld = (senales_url.get("tld_riesgo") or "bajo").lower()
    puntos, motivo = PESOS_TLD.get(riesgo_tld, (0, ""))
    anota("tld_riesgo", puntos, motivo)

    es_typosquat = bool(senales_url.get("es_typosquat"))
    if es_typosquat:
        marca = senales_url.get("marca_suplantada")
        motivo = (
            f"La dirección imita a la de {marca}" if marca
            else "La dirección imita a la de una marca conocida"
        )
        anota("typosquat", PUNTOS_TYPOSQUAT, motivo)

    if senales_url.get("es_acortador"):
        expandida = senales_url.get("url_expandida")
        motivo = "Usa un acortador que esconde el destino real"
        if expandida:
            motivo += f" (lleva a {expandida})"
        anota("acortador", PUNTOS_ACORTADOR, motivo)

    if senales_url.get("deep_link"):
        anota(
            "deep_link", PUNTOS_DEEP_LINK,
            f"Intenta abrir otra aplicación del móvil ({senales_url['deep_link']})",
        )

    # ---------------------------------------------------------- dinámicas
    error_sandbox = resultado_sandbox.get("error")
    hay_login = bool(resultado_sandbox.get("hay_formulario_login"))
    if hay_login:
        anota(
            "formulario_login", PUNTOS_FORMULARIO_LOGIN,
            "La página pide usuario y contraseña",
        )

    cadena = resultado_sandbox.get("cadena_redirecciones") or []
    saltos = max(len(cadena) - 1, 0)
    if saltos >= 3:
        anota(
            "redirecciones", PUNTOS_CADENA_REDIRECCIONES,
            f"La dirección da {saltos} saltos antes de llegar a su destino",
        )
    elif saltos >= 1:
        anota(
            "redirecciones", PUNTOS_ALGUNA_REDIRECCION,
            f"La dirección redirige a otra ({saltos} salto/s)",
        )

    dominio_inicial = _dominio(senales_url.get("url"))
    dominio_final = _dominio(resultado_sandbox.get("url_final"))
    cambia_de_dominio = bool(
        dominio_inicial and dominio_final and dominio_inicial != dominio_final
    )
    if cambia_de_dominio:
        anota(
            "cambio_dominio", PUNTOS_CAMBIO_DE_DOMINIO,
            f"Acaba en un dominio distinto del que anunciaba ({dominio_final})",
        )

    # ------------------------------------------------------------ combos
    dias = senales_url.get("edad_dominio_dias")
    if es_typosquat and hay_login:
        anota(
            "combo_suplantacion", PUNTOS_COMBO_TYPOSQUAT_LOGIN,
            "Imita a una marca Y además pide credenciales: patrón clásico de phishing",
        )
    if senales_url.get("es_acortador") and cambia_de_dominio:
        anota(
            "combo_acortador", PUNTOS_COMBO_ACORTADOR_OTRO_DOMINIO,
            "Esconde el destino tras un acortador y acaba en otro dominio distinto",
        )
    if hay_login and dias is not None and dias < 30:
        anota(
            "combo_dominio_nuevo", PUNTOS_COMBO_DOMINIO_NUEVO_LOGIN,
            "Pide credenciales en un dominio recién creado",
        )

    # ------------------------------------------------------------- nota
    nota = min(sum(d["puntos"] for d in detalle), NOTA_MAXIMA)

    if nota >= UMBRAL_PELIGRO:
        veredicto = "PELIGRO"
    elif nota >= UMBRAL_SOSPECHOSO:
        veredicto = "SOSPECHOSO"
    else:
        veredicto = "SEGURO"

    motivos = [d["motivo"] for d in sorted(detalle, key=lambda d: -d["puntos"])]

    if error_sandbox:
        # No hemos podido verla por dentro: lo decimos, no lo escondemos.
        motivos.append(
            f"⚠️ No se ha podido abrir la página para comprobarla ({error_sandbox}). "
            "El análisis se basa solo en la dirección."
        )
        if veredicto == "SEGURO":
            veredicto = "SOSPECHOSO" if nota >= 15 else veredicto

    if not motivos:
        motivos = ["No se han encontrado señales de riesgo"]

    return {
        "nota": nota,
        "veredicto": veredicto,
        "motivos": motivos,
        "detalle": detalle,
    }


def recomendacion(veredicto: str) -> str:
    """Frase de recomendación para el informe, según el veredicto."""
    return {
        "PELIGRO": "NO introduzcas ningún dato. Borra el mensaje y repórtalo.",
        "SOSPECHOSO": "No te fíes. Verifica por otro canal antes de hacer nada.",
        "SEGURO": "No se han detectado indicios de fraude, pero mantén la cautela.",
    }.get(veredicto, "Sin recomendación.")
