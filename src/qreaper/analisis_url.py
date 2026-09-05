"""
Módulo 2 — Análisis estático de URL  ·  Responsable: Alex (implementado por Jose)

Objetivo: dada una URL, buscarle pegas SIN abrirla. Devuelve dict de señales.

Filosofía: nunca revienta. Si whois no responde o la URL es rara, devolvemos
las claves con None y ya está. El pipeline se encarga de mezclar lo que haya.
Todas las claves del contrato salen siempre.
"""
from __future__ import annotations

import logging
import re
import socket
from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import urlparse, urlunparse

# python-whois escupe a stderr con print() cuando falla el socket. Le tapamos la boca.
logging.getLogger("whois").setLevel(logging.CRITICAL)

try:
    import whois  # type: ignore
except ImportError:  # el módulo puede faltar en máquinas sin internet
    whois = None  # type: ignore

try:
    import tldextract  # type: ignore
    _EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)
except ImportError:
    _EXTRACT = None  # type: ignore

try:
    import requests  # type: ignore
except ImportError:
    requests = None  # type: ignore


# ---------------------------------------------------------------------------
# Tablas. Tocar aquí para recalibrar (igual que scoring.py).
# ---------------------------------------------------------------------------

#: TLDs históricamente abusados por phishing (informes de APWG y Cofense).
TLD_ALTO_RIESGO = {
    "top", "xyz", "zip", "mov", "click", "link", "country", "gq", "tk",
    "ml", "cf", "ga", "cn", "ru", "biz", "info", "buzz", "kim", "loan",
    "review", "trade", "party", "science", "date", "racing", "download",
    "stream", "win", "bid", "cricket", "faith", "accountant", "webcam",
    "quest", "rest", "cyou", "monster", "makeup", "sbs",
}

#: Servicios DDNS gratuitos: te dan un subdominio en 30 segundos, muy usados
#: como aterrizaje de phishing porque no dejan rastro whois.
DDNS_GRATIS = {
    "duckdns.org", "no-ip.com", "no-ip.org", "no-ip.biz", "no-ip.info",
    "hopto.org", "zapto.org", "ddns.net", "dnsdynamic.org", "dynv6.net",
    "chickenkiller.com", "crabdance.com", "jumpingcrab.com", "mooo.com",
    "dynu.net", "dynu.com", "sytes.net", "servehttp.com", "myvnc.com",
    "publicvm.com", "myddns.rocks", "ignorelist.com",
}
TLD_MEDIO_RIESGO = {
    "online", "site", "shop", "store", "tech", "space", "website", "world",
    "life", "live", "app", "io", "co", "me", "cc", "ws", "vip",
}
# El resto (com, es, org, net, gov, edu, uk, de, fr...) se considera bajo.

#: Marcas suplantadas con frecuencia en España + globales top.
MARCAS_ES = {
    "correos", "aeat", "agenciatributaria", "seg-social", "seguridadsocial",
    "dgt", "bbva", "santander", "caixabank", "lacaixa", "bankinter",
    "sabadell", "ing", "openbank", "unicaja", "kutxabank", "abanca",
    "endesa", "iberdrola", "naturgy", "movistar", "vodafone", "orange",
    "yoigo", "masmovil", "amazon", "aliexpress", "netflix", "paypal",
    "apple", "google", "microsoft", "outlook", "office365", "instagram",
    "facebook", "whatsapp", "correoscash", "burofax", "iberia", "renfe",
    "elcorteingles", "mediamarkt", "leroymerlin", "worten", "carrefour",
    "mercadona", "hacienda", "policia", "guardiacivil", "notaria",
}

#: Acortadores conocidos. Al primer contacto expandimos con HEAD (sin GET).
ACORTADORES = {
    "bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "buff.ly",
    "is.gd", "cutt.ly", "rebrand.ly", "shorturl.at", "rb.gy",
    "t.ly", "s.id", "lnkd.in", "fb.me", "youtu.be", "amzn.to",
    "wa.me", "chng.it", "acortar.link", "acortar.co",
}

#: Esquemas de deep-link que un QR puede llevar (peligrosos porque saltan a otra app).
ESQUEMAS_DEEPLINK = {
    "intent", "market", "whatsapp", "tg", "telegram", "viber", "skype",
    "fb", "twitter", "spotify", "zoom", "slack", "geo", "mailto", "tel",
    "sms", "smsto", "matmsg", "wifi",  # los últimos son típicos QR
}

DEEPLINK_RE = re.compile(r"^([a-z][a-z0-9+.\-]*):", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dominio_registrable(host: str) -> tuple[str, str, str]:
    """(subdominio, dominio, tld) usando tldextract si está, si no fallback tosco.

    Falta el suffix_list local: si tldextract cache está vacío, cae al fallback.
    """
    host = (host or "").lower().strip(".")
    if not host:
        return ("", "", "")
    if _EXTRACT is not None:
        try:
            ex = _EXTRACT(host)
            if ex.domain and ex.suffix:
                return (ex.subdomain, ex.domain, ex.suffix)
        except Exception:
            pass
    # Fallback: el último trozo es el TLD, el penúltimo el dominio.
    partes = host.split(".")
    if len(partes) >= 2:
        return (".".join(partes[:-2]), partes[-2], partes[-1])
    return ("", host, "")


def _clasificar_tld(tld: str, host: str = "") -> str:
    """Clasifica el TLD. Los DDNS gratis (duckdns.org, no-ip.com...) suben a alto."""
    host = (host or "").lower()
    for ddns in DDNS_GRATIS:
        if host == ddns or host.endswith("." + ddns):
            return "alto"
    tld = (tld or "").lower().split(".")[-1]  # de "co.uk" cogemos "uk"
    if not tld:
        return "bajo"
    if tld in TLD_ALTO_RIESGO:
        return "alto"
    if tld in TLD_MEDIO_RIESGO:
        return "medio"
    return "bajo"


def _damerau_levenshtein(a: str, b: str) -> int:
    """Distancia con transposiciones (ba <-> ab cuenta 1, no 2)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    # matriz (la+1) x (lb+1)
    dp = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        dp[i][0] = i
    for j in range(lb + 1):
        dp[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            coste = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,        # borrado
                dp[i][j - 1] + 1,        # inserción
                dp[i - 1][j - 1] + coste,  # sustitución
            )
            if (
                i > 1 and j > 1
                and a[i - 1] == b[j - 2]
                and a[i - 2] == b[j - 1]
            ):
                dp[i][j] = min(dp[i][j], dp[i - 2][j - 2] + 1)
    return dp[la][lb]


# Homoglifos comunes usados en typosquat cirílico/griego a latino.
HOMOGLIFOS = str.maketrans({
    # cirílicos que se ven igual que latinos
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ɡ": "g", "ⅼ": "l", "ⅿ": "m",
    # dígitos que suplantan letras (leetspeak clásico de typosquat)
    "0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t",
})


def _normaliza_para_comparar(s: str) -> str:
    """Baja a minúsculas, quita homoglifos y guiones para comparar con marcas."""
    return s.translate(HOMOGLIFOS).lower().replace("-", "")


def _detectar_typosquat(subdominio: str, dominio: str) -> tuple[bool, str | None]:
    """Devuelve (es_typosquat, marca_suplantada).

    Reglas (por orden):
      1) Alguna palabra del host, normalizada (leetspeak + homoglifos), coincide
         con una marca conocida — y el original NO coincide: "c0rreos", "netfl1x",
         "verificar-bbva".
      2) Distancia edit ≤ 1 entre una palabra normalizada y la marca: "corr3os",
         "goggle" (fallo de tecla).
      3) Marca como sub-cadena en el dominio (≥5): "correos-verificar".
      4) El dominio original coincide con la marca (correos.es) → NO typosquat.
    """
    if not dominio:
        return (False, None)

    # Split ANTES de normalizar (para no perder guiones).
    partes_dom = [p for p in re.split(r"[.\-_]+", dominio) if p]
    partes_sub = [p for p in re.split(r"[.\-_]+", subdominio or "") if p]
    todas = [(p, _normaliza_para_comparar(p)) for p in partes_dom + partes_sub]
    dominio_norm = _normaliza_para_comparar(dominio)

    # El dominio registrable (sin subdominio) tal cual: "bbva", "correos".
    dominio_original = dominio.lower() if len(partes_dom) == 1 else ""

    for marca in MARCAS_ES:
        m = marca.lower()

        # Excepción: dominio registrable = marca → LEGÍTIMO (bbva.com, correos.es,
        # cliente.bbva.com...). Cualquier subdominio ahí es de la marca de verdad.
        if dominio_original == m:
            continue

        # 1) alguna palabra (dominio o subdominio) coincide con la marca tras normalizar
        if any(norm == m for _, norm in todas):
            return (True, marca)

        # 2) distancia edit ≤ 1 sobre cualquier palabra ≥4 chars
        if len(m) >= 4:
            for _, norm in todas:
                if (
                    norm != m
                    and abs(len(norm) - len(m)) <= 1
                    and _damerau_levenshtein(norm, m) <= 1
                ):
                    return (True, marca)

        # 3) sub-cadena larga en el dominio normalizado
        if len(m) >= 5 and m in dominio_norm and dominio_norm != m:
            return (True, marca)

    return (False, None)


@lru_cache(maxsize=256)
def _edad_dominio_dias(dominio_registrable: str) -> int | None:
    """Días desde la creación del dominio. None si whois no responde."""
    if not dominio_registrable or whois is None:
        return None
    try:
        socket.setdefaulttimeout(5)
        w = whois.whois(dominio_registrable)
    except Exception:
        return None
    fecha = getattr(w, "creation_date", None)
    if isinstance(fecha, list):
        fecha = fecha[0] if fecha else None
    if not fecha:
        return None
    if isinstance(fecha, str):
        # Algunos registrars devuelven ISO en string.
        try:
            fecha = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(fecha, datetime):
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    ahora = datetime.now(timezone.utc)
    return max((ahora - fecha).days, 0)


def _expandir_acortador(url: str, host: str) -> str | None:
    """HEAD al acortador, cogemos Location. Sin abrir cuerpo, sin JS."""
    if host not in ACORTADORES or requests is None:
        return None
    try:
        r = requests.head(
            url, allow_redirects=False, timeout=4,
            headers={"User-Agent": "QReaper/1.0 (+static-check)"},
        )
    except Exception:
        return None
    destino = r.headers.get("Location")
    if not destino:
        return None
    return destino[:2048]


def _extraer_deeplink(url: str) -> str | None:
    """Devuelve el esquema si es un deep-link peligroso (intent://, tg://, etc.)."""
    m = DEEPLINK_RE.match(url or "")
    if not m:
        return None
    esquema = m.group(1).lower()
    if esquema in {"http", "https"}:
        return None
    if esquema in ESQUEMAS_DEEPLINK:
        return f"{esquema}://"
    # Cualquier esquema no estándar es sospechoso.
    return f"{esquema}://"


def _normaliza_idn(url: str) -> str:
    """Pasa hostnames IDN a punycode para poder comparar bien."""
    try:
        p = urlparse(url)
        host = p.hostname
        if not host:
            return url
        host_puny = host.encode("idna").decode("ascii")
        netloc = host_puny
        if p.port:
            netloc = f"{host_puny}:{p.port}"
        return urlunparse(p._replace(netloc=netloc))
    except Exception:
        return url


# ---------------------------------------------------------------------------
# API pública (contrato)
# ---------------------------------------------------------------------------


def analizar_url(url: str) -> dict:
    """Analiza una URL de forma estática y devuelve señales de riesgo.

    Cumple el contrato: siempre devuelve las 8 claves. Si algo no se puede
    averiguar (whois offline, TLD raro, etc.), esa clave viene con ``None``.
    """
    url = (url or "").strip()

    # Todas las claves del contrato, con default por si algo se cae luego.
    senales: dict = {
        "url": url,
        "edad_dominio_dias": None,
        "tld_riesgo": "bajo",
        "es_typosquat": False,
        "marca_suplantada": None,
        "es_acortador": False,
        "url_expandida": None,
        "deep_link": None,
    }

    if not url:
        return senales

    # 1) deep-link primero: si no es http/https, poco más se puede analizar.
    deep = _extraer_deeplink(url)
    if deep and not url.lower().startswith(("http://", "https://")):
        senales["deep_link"] = deep
        return senales
    if deep:
        senales["deep_link"] = deep

    url_norm = _normaliza_idn(url)
    parsed = urlparse(url_norm)
    host = (parsed.hostname or "").lower()
    if not host:
        return senales

    subdominio, dominio, tld = _dominio_registrable(host)
    dominio_registrable = f"{dominio}.{tld}" if dominio and tld else host

    # 2) TLD (DDNS gratis suben a alto por host completo)
    senales["tld_riesgo"] = _clasificar_tld(tld, host)

    # 3) typosquat / homoglifos (comparamos también contra host completo)
    es_ts, marca = _detectar_typosquat(subdominio, dominio)
    senales["es_typosquat"] = es_ts
    senales["marca_suplantada"] = marca

    # 4) edad del dominio (puede tardar; whois con timeout)
    senales["edad_dominio_dias"] = _edad_dominio_dias(dominio_registrable)

    # 5) acortador + expansión
    if host in ACORTADORES:
        senales["es_acortador"] = True
        senales["url_expandida"] = _expandir_acortador(url_norm, host)

    return senales


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("uso: python -m qreaper.analisis_url <url>")
        sys.exit(1)
    print(json.dumps(analizar_url(sys.argv[1]), indent=2, ensure_ascii=False))
