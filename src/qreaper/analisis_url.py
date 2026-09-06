# -*- coding: utf-8 -*-
"""
Modulo 2 - Analisis estatico de URL  ·  Responsable: Alex

Objetivo: dada una URL, buscarle pegas SIN abrirla. Devuelve dict de senales.

Contrato de salida (ver CONTRATOS.md):

    {
      "url":               str,           # la URL tal cual entro
      "edad_dominio_dias": int | None,    # None si el whois no responde
      "tld_riesgo":        "bajo" | "medio" | "alto",
      "es_typosquat":      bool,
      "marca_suplantada":  str | None,
      "es_acortador":      bool,
      "url_expandida":     str | None,    # destino real del acortador
      "deep_link":         str | None,    # si el esquema no es http(s)
      "detalle":           dict,          # extra no contractual (motivos, whois...)
    }

Nota sobre "sin abrirla": el unico trafico que genera este modulo es
(a) consultas whois y (b) peticiones HEAD para expandir acortadores, que no
descargan el cuerpo ni ejecutan JavaScript. Detonar la URL de verdad es
trabajo del modulo 3 (sandbox). Ambas cosas se pueden apagar:

    analizar_url(url, whois_activo=False, expandir_acortadores=False)

Uso por CLI (desde la carpeta src/):
    python -m qreaper.analisis_url "https://correos-es.top/pago"
    python -m qreaper.analisis_url --sin-red --json "https://correos-es.top/pago"
"""
from __future__ import annotations

import ipaddress
import json
import re
import sys
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin, parse_qs, unquote

from .datos_url import (
    ACORTADORES,
    DOMINIOS_LEGITIMOS,
    BIGRAMAS_HOMOGLIFOS,
    ESQUEMAS_APP,
    EXTENSIONES_PELIGROSAS,
    HOMOGLIFOS,
    MARCAS,
    MARCAS_CORTAS,
    PALABRAS_GANCHO,
    PARAMS_REDIRECCION,
    TLD_ALTO,
    TLD_MEDIO,
    USER_AGENT,
)

# --- dependencias opcionales -------------------------------------------
# El modulo tiene que seguir dando un veredicto aunque falte una libreria
# o no haya red: degrada, no revienta.
try:
    import tldextract
    # suffix_list_urls=() -> usa la lista publica de sufijos que trae el
    # paquete y NO sale a internet. Analisis reproducible y sin esperas.
    _EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())
except Exception:                                   # pragma: no cover
    tldextract = None
    _EXTRACTOR = None

try:
    import whois as _whois
except Exception:                                   # pragma: no cover
    _whois = None

try:
    import requests
except Exception:                                   # pragma: no cover
    requests = None


# =======================================================================
# Utilidades de texto y dominio
# =======================================================================

# Caracteres invisibles que se cuelan al copiar una URL de un correo.
_INVISIBLES = "​‌‍⁠﻿­"
_RE_ESQUEMA = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")


def limpiar(url: str) -> str:
    """Quita adornos que trae la URL cuando sale de un correo o un PDF."""
    u = (url or "").strip()
    for c in _INVISIBLES:
        u = u.replace(c, "")
    # Se repite hasta que deja de cambiar: en un PDF es normal encontrar
    # <https://ejemplo.es/x>. con corchetes Y el punto final de la frase.
    anterior = None
    while u != anterior:
        anterior = u
        u = u.strip("<>[]\"'` \t\r\n")
        while u and u[-1] in ".,;:)]}":
            # ...salvo que el parentesis fuera parte de la propia URL.
            if u[-1] == ")" and u.count("(") >= u.count(")"):
                break
            u = u[:-1]
    return u


def decodificar_punycode(host: str) -> str:
    """xn--crreos-9va.es -> correos.es (para ver el nombre como lo ve la victima)."""
    salida = []
    for etiqueta in host.split("."):
        if etiqueta.lower().startswith("xn--"):
            try:
                salida.append(etiqueta[4:].encode("ascii").decode("punycode"))
            except Exception:
                salida.append(etiqueta)
        else:
            salida.append(etiqueta)
    return ".".join(salida)


def esqueleto(texto: str) -> str:
    """Normaliza un texto para comparar marcas.

    Aplana acentos, pasa homoglifos (cirilico, griego, digitos) a su letra
    latina y resuelve bigramas del tipo 'rn' -> 'm'. Asi 'c0rre0s' y
    'correos' (con 'o' cirilica) acaban siendo la misma cadena.
    """
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = "".join(HOMOGLIFOS.get(c, c) for c in t)
    for par, letra in BIGRAMAS_HOMOGLIFOS:
        t = t.replace(par, letra)
    return t


def distancia(a: str, b: str) -> int:
    """Distancia de edicion (Levenshtein). Cuantos retoques hay de a a b."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    fila = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        nueva = [i]
        for j, cb in enumerate(b, 1):
            nueva.append(min(fila[j] + 1, nueva[j - 1] + 1, fila[j - 1] + (ca != cb)))
        fila = nueva
    return fila[-1]


def _es_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


# Sufijos de dos niveles mas habituales, para el plan B sin tldextract.
_SUFIJOS_DOBLES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.es", "gob.es", "org.es",
    "com.ar", "com.br", "com.mx", "com.co", "com.pe", "com.au", "net.au",
    "co.jp", "ne.jp", "co.kr", "com.tr", "com.cn", "co.nz", "co.za",
    "com.pt", "com.uy", "com.ve", "co.in", "org.in",
}


def _partir_host(host: str) -> tuple[str, str, str]:
    """(subdominio, dominio, sufijo). Usa tldextract si esta; si no, heuristica."""
    if _EXTRACTOR is not None:
        try:
            p = _EXTRACTOR(host)
            return p.subdomain, p.domain, p.suffix
        except Exception:
            pass
    etiquetas = host.split(".")
    if len(etiquetas) < 2:
        return "", host, ""
    if len(etiquetas) >= 3 and ".".join(etiquetas[-2:]) in _SUFIJOS_DOBLES:
        return ".".join(etiquetas[:-3]), etiquetas[-3], ".".join(etiquetas[-2:])
    return ".".join(etiquetas[:-2]), etiquetas[-2], etiquetas[-1]


# =======================================================================
# 1. TLD
# =======================================================================

def riesgo_tld(sufijo: str) -> str:
    """Clasifica el TLD. Se mira la ultima etiqueta (co.uk -> uk)."""
    if not sufijo:
        return "alto"          # sin TLD valido: IP literal o host raro
    ultimo = sufijo.lower().rsplit(".", 1)[-1]
    if ultimo in TLD_ALTO:
        return "alto"
    if ultimo in TLD_MEDIO:
        return "medio"
    return "bajo"


# =======================================================================
# 2. Edad del dominio (whois)
# =======================================================================

_CACHE_WHOIS: dict[str, dict] = {}

_FORMATOS_FECHA = (
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
    "%d-%b-%Y", "%d.%m.%Y", "%Y/%m/%d",
)


def _a_fecha(valor) -> datetime | None:
    """El whois devuelve fechas en mil formatos: datetime, lista o texto."""
    if isinstance(valor, list):
        fechas = [f for f in (_a_fecha(v) for v in valor) if f]
        return min(fechas) if fechas else None
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None) if valor.tzinfo else valor
    if isinstance(valor, str):
        texto = valor.strip().replace("Z", "").split(".")[0]
        for fmt in _FORMATOS_FECHA:
            try:
                return datetime.strptime(texto, fmt)
            except ValueError:
                continue
    return None


class _FiltroSalida:
    """Envoltorio de sys.stdout/stderr que silencia SOLO al hilo del whois.

    python-whois escribe sus errores de socket con print(). No sirve
    redirect_stdout: es global al proceso, y si el whois se queda colgado
    en su hilo se traga tambien lo que imprime el programa principal (y
    rompe la salida --json). Con un flag por hilo cada uno va a lo suyo.
    """
    _local = threading.local()
    _instalado = False

    def __init__(self, real):
        self._real = real

    @classmethod
    def silenciar_hilo_actual(cls) -> None:
        cls._local.mudo = True

    @classmethod
    def instalar(cls) -> None:
        if not cls._instalado:
            sys.stdout = cls(sys.stdout)
            sys.stderr = cls(sys.stderr)
            cls._instalado = True

    def write(self, texto):
        if getattr(self._local, "mudo", False):
            return len(texto)
        return self._real.write(texto)

    def flush(self):
        if not getattr(self._local, "mudo", False):
            self._real.flush()

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)


def _whois_silencioso(dominio: str):
    _FiltroSalida.silenciar_hilo_actual()
    return _whois.whois(dominio)


def _via_whois(dominio: str, timeout: float) -> dict:
    """Whois clasico (puerto 43) con tope de tiempo.

    python-whois puede quedarse colgado contra servidores lentos, asi que
    la llamada va en un hilo aparte del que nos desenganchamos al vencer
    el plazo (el hilo morira solo; lo que no puede es bloquear el analisis).
    """
    if _whois is None:
        return {"error": "python-whois no instalado"}
    _FiltroSalida.instalar()
    ejecutor = ThreadPoolExecutor(max_workers=1)
    try:
        crudo = ejecutor.submit(_whois_silencioso, dominio).result(timeout=timeout)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"[:200]}
    finally:
        ejecutor.shutdown(wait=False, cancel_futures=True)
    if not crudo:
        return {"error": "el whois no devuelve datos"}
    return {
        "creacion": _a_fecha(crudo.get("creation_date")),
        "expiracion": _a_fecha(crudo.get("expiration_date")),
        "actualizacion": _a_fecha(crudo.get("updated_date")),
        "registrador": crudo.get("registrar"),
        "pais": crudo.get("country"),
        "fuente": "whois",
    }


def _via_rdap(dominio: str, timeout: float) -> dict:
    """Plan B: RDAP, el sustituto moderno del whois.

    Devuelve JSON en vez de texto libre, va por HTTPS y no se cuelga como
    el puerto 43. Cubre los gTLD (.com, .top, .xyz...); los ccTLD como .es
    no publican RDAP abierto, asi que ahi seguiremos sin fecha.
    """
    if requests is None:
        return {"error": "requests no instalado"}
    try:
        r = requests.get(f"https://rdap.org/domain/{dominio}",
                         timeout=timeout,
                         headers={"User-Agent": "QReaper/1.0",
                                  "Accept": "application/rdap+json"})
        if r.status_code != 200:
            return {"error": f"rdap HTTP {r.status_code}"}
        datos = r.json()
    except Exception as exc:
        return {"error": f"rdap {type(exc).__name__}"}

    eventos = {e.get("eventAction"): e.get("eventDate")
               for e in datos.get("events", []) if isinstance(e, dict)}
    registrador = None
    for ent in datos.get("entities", []):
        if "registrar" in (ent.get("roles") or []):
            for campo in (ent.get("vcardArray") or [[], []])[1]:
                if campo and campo[0] == "fn":
                    registrador = campo[3]
            break
    return {
        "creacion": _a_fecha(eventos.get("registration")),
        "expiracion": _a_fecha(eventos.get("expiration")),
        "actualizacion": _a_fecha(eventos.get("last changed")),
        "registrador": registrador,
        "pais": None,
        "fuente": "rdap",
    }


def consultar_whois(dominio: str, timeout: float = 8.0) -> dict:
    """Datos de registro del dominio, con cache. Devuelve siempre un dict.

    Primero whois y, si no da fecha de creacion, RDAP. Que no haya datos
    NO es una senal de nada: muchos ccTLD (.es el primero) no publican
    whois abierto. En ese caso 'edad_dias' vale None y el modulo 4 debe
    puntuar con el resto de senales.
    """
    if dominio in _CACHE_WHOIS:
        return _CACHE_WHOIS[dominio]

    info = _via_whois(dominio, timeout)
    if not info.get("creacion"):
        alterno = _via_rdap(dominio, min(timeout, 6.0))
        if alterno.get("creacion"):
            info = alterno
        else:
            info.setdefault("error", alterno.get("error", "sin datos de registro"))

    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    creado, caduca = info.get("creacion"), info.get("expiracion")
    actualizado = info.get("actualizacion")
    resultado = {
        "creacion": creado.isoformat() if creado else None,
        "expiracion": caduca.isoformat() if caduca else None,
        "actualizacion": actualizado.isoformat() if actualizado else None,
        "edad_dias": (ahora - creado).days if creado else None,
        "dias_para_caducar": (caduca - ahora).days if caduca else None,
        "registrador": info.get("registrador"),
        "pais": info.get("pais"),
        "fuente": info.get("fuente"),
    }
    if creado is None:
        resultado["error"] = info.get("error", "sin fecha de creacion")
    _CACHE_WHOIS[dominio] = resultado
    return resultado


def edad_en_dias(dominio: str, timeout: float = 8.0) -> int | None:
    """Dias desde que se registro el dominio. None si el whois no contesta."""
    return consultar_whois(dominio, timeout).get("edad_dias")


# =======================================================================
# 3. Typosquatting / suplantacion de marca
# =======================================================================

_SEPARADORES = re.compile(r"[^a-z0-9]+")


def _marca_en(texto: str, marca: str) -> bool:
    """La marca aparece como palabra dentro del texto (no dentro de otra)."""
    if marca in MARCAS_CORTAS:
        # Marcas de 3-4 letras: solo si van delimitadas, para no cazar
        # "dgt" dentro de "widgets" ni "ups" dentro de "groups".
        return any(t == marca for t in _SEPARADORES.split(texto) if t)
    return marca in texto


def detectar_marca(host: str, ruta: str = "",
                   usuario: str = "") -> tuple[bool, str | None, str | None]:
    """Busca suplantacion de marca en el host (y de rebote en ruta y userinfo).

    Devuelve (es_typosquat, marca, tecnica). La comparacion se hace SIEMPRE
    contra el dominio registrable, nunca contra la cadena entera: eso es
    justo lo que explota el truco de 'correos.es.pago-pendiente.top'.
    """
    subdominio, dominio, sufijo = _partir_host(host)
    registrable = f"{dominio}.{sufijo}".strip(".").lower()
    label = esqueleto(dominio)
    sub_esq = esqueleto(subdominio)
    ruta_esq = esqueleto(unquote(ruta))
    usuario_esq = esqueleto(unquote(usuario))

    # 0) Dominio legitimo: se corta aqui para no dar falsos positivos.
    if registrable in DOMINIOS_LEGITIMOS:
        return False, None, None

    candidatas: list[tuple[int, str, str]] = []   # (prioridad, marca, tecnica)

    for marca, legitimos in MARCAS.items():
        m = esqueleto(marca)

        # 1) El esqueleto del label ES la marca. O el nombre esta escrito
        #    igual y solo cambia el TLD (correos.top, netflix.xyz), o lo han
        #    escrito con homoglifos (c0rre0s, corre0s, correos con o cirilica).
        if label == m:
            if dominio.lower() == marca:
                candidatas.append((0, marca, "marca con TLD que no es el suyo"))
            else:
                candidatas.append((0, marca, "homoglifos"))
            continue

        # 2) Una letra cambiada, sobrante o de menos: correros, bbwa, arnazon.
        #    El umbral depende del largo: en marcas de 3 letras cualquier
        #    dominio corto quedaria a distancia 1, asi que no se aplica.
        if len(m) <= 3:
            umbral, solo_sustitucion = 0, True
        elif len(m) <= 4:
            umbral, solo_sustitucion = 1, True   # bbva -> bbwa, pero no sur -> seur
        elif len(m) <= 6:
            umbral, solo_sustitucion = 1, False
        else:
            umbral, solo_sustitucion = 2, False
        dif_largo = abs(len(label) - len(m))
        if umbral and (dif_largo == 0 if solo_sustitucion else dif_largo <= umbral) \
                and distancia(label, m) <= umbral:
            candidatas.append((1, marca, "letra cambiada (distancia de edicion)"))
            continue

        # 3) La marca dentro del label con relleno: correos-es, pagocorreos,
        #    dgt-multas, correos-seguimiento. En marcas cortas _marca_en ya
        #    exige que vaya delimitada.
        if _marca_en(label, m):
            candidatas.append((2, marca, "marca con texto anadido en el dominio"))
            continue

        # 4) La marca en el subdominio: correos.es.pago-pendiente.top
        if sub_esq and _marca_en(sub_esq, m):
            candidatas.append((3, marca, "marca en el subdominio"))
            continue

        # 5) La marca en el texto anterior al @: https://correos.es@malo.top
        #    Ese trozo es puramente decorativo, el navegador lo ignora.
        if usuario_esq and _marca_en(usuario_esq, m):
            candidatas.append((3, marca, "marca antes del @ (texto decorativo)"))
            continue

        # 6) La marca solo en la ruta: pago-seguro.top/correos/envio
        if ruta_esq and _marca_en(ruta_esq, m):
            candidatas.append((4, marca, "marca en la ruta"))

    if not candidatas:
        return False, None, None
    candidatas.sort(key=lambda c: (c[0], -len(c[1])))
    _, marca, tecnica = candidatas[0]
    return True, marca, tecnica


# =======================================================================
# 4. Acortadores
# =======================================================================

def es_acortador(host: str) -> bool:
    h = host.lower().lstrip(".")
    if h.startswith("www."):
        h = h[4:]
    return h in ACORTADORES


def expandir(url: str, timeout: float = 5.0, max_saltos: int = 10) -> tuple[str | None, list[str], str | None]:
    """Sigue la cadena de redirecciones de un acortador.

    Va salto a salto con HEAD (allow_redirects=False) para quedarse con la
    cadena entera, que es la parte interesante: un acortador que acaba en
    un dominio recien registrado o en un deep-link canta mucho.
    No descarga el cuerpo ni ejecuta JavaScript: las redirecciones por
    meta-refresh o por JS las vera el modulo 3.

    Devuelve (url_final, cadena, error).
    """
    if requests is None:
        return None, [url], "requests no instalado"

    cabeceras = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    cadena = [url]
    actual = url
    try:
        with requests.Session() as sesion:
            sesion.max_redirects = max_saltos
            for _ in range(max_saltos):
                try:
                    r = sesion.head(actual, allow_redirects=False,
                                    timeout=timeout, headers=cabeceras)
                except requests.RequestException:
                    r = None
                # Hay servidores que no admiten HEAD: se reintenta con GET
                # en streaming y se cierra sin leer el cuerpo.
                if r is None or r.status_code in (400, 403, 405, 501):
                    r = sesion.get(actual, allow_redirects=False, timeout=timeout,
                                   headers=cabeceras, stream=True)
                    r.close()
                destino = r.headers.get("Location")
                if not destino or not (300 <= r.status_code < 400):
                    break
                actual = urljoin(actual, destino)
                if actual in cadena:
                    return actual, cadena, "bucle de redirecciones"
                cadena.append(actual)
            else:
                return actual, cadena, "demasiadas redirecciones"
    except Exception as exc:
        return None, cadena, f"{type(exc).__name__}: {exc}"[:200]

    return actual, cadena, None


# =======================================================================
# 5. Deep links
# =======================================================================

def detectar_deep_link(url: str) -> tuple[str | None, str | None]:
    """Si el esquema no es http(s), la URL abre una app: siempre sospechoso."""
    esquema = urlparse(url).scheme.lower()
    if esquema in ("http", "https", ""):
        return None, None
    return url, ESQUEMAS_APP.get(esquema, f"esquema no web '{esquema}'")


# =======================================================================
# Orquestador
# =======================================================================

def _motivo(motivos: list, codigo: str, peso: int, texto: str) -> None:
    motivos.append({"codigo": codigo, "peso": peso, "texto": texto})


def _puntuar(motivos: list[dict]) -> int:
    """Combina los pesos con OR probabilistico (ruidoso).

    Sumar pesos satura enseguida y cualquier URL larga acaba en 100. Asi,
    cada senal reduce la probabilidad de que la URL sea buena y ninguna
    llega sola al maximo: 100 * (1 - producto(1 - peso/100)).
    """
    bueno = 1.0
    for m in motivos:
        bueno *= 1 - min(max(m["peso"], 0), 95) / 100
    return int(round(100 * (1 - bueno)))


def _nivel(puntuacion: int) -> str:
    if puntuacion >= 70:
        return "critico"
    if puntuacion >= 45:
        return "alto"
    if puntuacion >= 20:
        return "medio"
    return "bajo"


def analizar_url(url: str,
                 *,
                 whois_activo: bool = True,
                 expandir_acortadores: bool = True,
                 timeout: float = 5.0,
                 _profundidad: int = 0) -> dict:
    """Analiza una URL de forma estatica y devuelve senales de riesgo.

    Los tres pasos que puede hacer red (whois y expansion de acortadores)
    se pueden apagar con los parametros; el resto es 100% offline.
    """
    motivos: list[dict] = []
    original = url or ""
    limpia = limpiar(original)

    if not limpia:
        return {
            "url": original, "edad_dominio_dias": None, "tld_riesgo": "alto",
            "es_typosquat": False, "marca_suplantada": None,
            "es_acortador": False, "url_expandida": None, "deep_link": None,
            "detalle": {"error": "URL vacia", "motivos": [], "puntuacion": 0,
                        "nivel": "bajo"},
        }

    # --- deep link ------------------------------------------------------
    deep_link, app = detectar_deep_link(limpia)
    if deep_link:
        _motivo(motivos, "deep_link", 70,
                f"No es una direccion web: intenta abrir {app}. "
                "El usuario nunca ve el destino real al escanear.")

    # --- esquema --------------------------------------------------------
    sin_esquema = _RE_ESQUEMA.match(limpia) is None
    trabajo = ("http://" + limpia) if sin_esquema else limpia
    if sin_esquema:
        _motivo(motivos, "sin_esquema", 10, "La URL no indica protocolo.")

    partes = urlparse(trabajo)
    if partes.scheme == "http":
        _motivo(motivos, "sin_tls", 25, "Va por HTTP sin cifrar.")

    # Credenciales embebidas: https://correos.es@dominio-malo.top
    # El navegador va a dominio-malo.top; el usuario lee correos.es.
    if "@" in partes.netloc:
        _motivo(motivos, "userinfo", 75,
                "La URL lleva un '@': lo que se lee antes del arroba es "
                "decorado, el destino real es lo que va detras.")

    # --- acortador y expansion -----------------------------------------
    host = (partes.hostname or "").lower().rstrip(".")
    acortador = bool(host) and es_acortador(host)
    url_expandida = None
    cadena: list[str] = []
    error_expansion = None

    if acortador:
        _motivo(motivos, "acortador", 30,
                f"Usa el acortador {host}: el destino real esta oculto.")
        if expandir_acortadores:
            final, cadena, error_expansion = expandir(trabajo, timeout=timeout)
            if final and final != trabajo:
                url_expandida = final
            elif error_expansion:
                _motivo(motivos, "acortador_no_expandido", 15,
                        f"No se ha podido resolver el acortador ({error_expansion}).")

    # A partir de aqui se analiza el DESTINO, que es donde esta la trampa.
    url_analizada = url_expandida or trabajo
    partes_an = urlparse(url_analizada)
    host_an = (partes_an.hostname or "").lower().rstrip(".")
    ruta = (partes_an.path or "") + ("?" + partes_an.query if partes_an.query else "")

    if url_expandida:
        dl_final, app_final = detectar_deep_link(url_expandida)
        if dl_final and not deep_link:
            deep_link = url_expandida
            _motivo(motivos, "acortador_a_deep_link", 80,
                    f"El acortador termina abriendo {app_final}.")

    # --- host, dominio, TLD --------------------------------------------
    subdominio, dominio_label, sufijo = _partir_host(host_an) if host_an else ("", "", "")
    dominio = f"{dominio_label}.{sufijo}".strip(".")
    es_ip = _es_ip(host_an) if host_an else False
    host_unicode = decodificar_punycode(host_an) if host_an else ""

    if es_ip:
        dominio = host_an
        tld_riesgo = "alto"
        _motivo(motivos, "host_ip", 60,
                "El enlace apunta a una IP, no a un nombre de dominio: "
                "ningun servicio legitimo hace eso en un QR.")
    else:
        tld_riesgo = riesgo_tld(sufijo)
        # Sin sufijo no hay TLD que juzgar (pasa en los deep-link, donde el
        # "host" es un comando de la app). Ahi ya puntua la senal deep_link:
        # anadir tld_alto seria contar dos veces lo mismo.
        if not sufijo:
            pass
        elif tld_riesgo == "alto":
            _motivo(motivos, "tld_alto", 45,
                    f"El dominio de primer nivel .{sufijo} es de los mas "
                    "usados para fraude (registro barato y sin verificar).")
        elif tld_riesgo == "medio":
            _motivo(motivos, "tld_medio", 20,
                    f"El dominio de primer nivel .{sufijo} tiene abuso frecuente.")

    if "xn--" in host_an:
        _motivo(motivos, "punycode", 55,
                f"El dominio usa punycode: se muestra como '{host_unicode}' "
                "pero por dentro es otro nombre.")

    n_sub = len([s for s in subdominio.split(".") if s]) if subdominio else 0
    if n_sub >= 3:
        _motivo(motivos, "muchos_subdominios", 25,
                f"{n_sub} subdominios encadenados: se usan para colar el "
                "nombre de la marca donde el movil corta el texto.")
    # Los guiones se cuentan sobre el nombre ya descodificado: un dominio
    # punycode los lleva por construccion (xn--crreos-wxa) y no significan
    # nada. Eso ya lo denuncia la senal 'punycode'.
    label_legible = _partir_host(host_unicode)[1] if host_unicode else ""
    if not es_ip and label_legible.count("-") >= 2:
        _motivo(motivos, "guiones", 15,
                "El dominio encadena varias palabras con guiones.")
    if len(url_analizada) > 120:
        _motivo(motivos, "url_larga", 10,
                f"URL de {len(url_analizada)} caracteres.")
    if partes_an.port and partes_an.port not in (80, 443):
        _motivo(motivos, "puerto", 30,
                f"Usa el puerto {partes_an.port}, fuera de lo normal en web.")

    # --- typosquatting --------------------------------------------------
    # El texto anterior al @ se analiza aparte: no es el host, pero es lo
    # que lee la victima.
    usuario = partes_an.netloc.split("@")[0] if "@" in partes_an.netloc else ""
    if host_an and not es_ip:
        typosquat, marca, tecnica = detectar_marca(host_unicode, ruta, usuario)
    else:
        typosquat, marca, tecnica = False, None, None

    if typosquat:
        legitimos = ", ".join(MARCAS.get(marca, ()))
        peso = 85 if tecnica and "ruta" not in tecnica else 45
        _motivo(motivos, "typosquat", peso,
                f"Imita a {marca} ({tecnica}). El dominio real es "
                f"'{dominio}', no {legitimos}.")

    # --- lexico y ruta --------------------------------------------------
    texto_url = esqueleto(unquote(url_analizada))
    ganchos = sorted({p for p in PALABRAS_GANCHO if p in texto_url})
    if len(ganchos) >= 2:
        _motivo(motivos, "palabras_gancho", 20,
                "Palabras de gancho en la URL: " + ", ".join(ganchos[:6]) + ".")
    elif ganchos:
        _motivo(motivos, "palabras_gancho", 10,
                f"Palabra de gancho en la URL: {ganchos[0]}.")

    ruta_baja = partes_an.path.lower()
    for ext in EXTENSIONES_PELIGROSAS:
        if ruta_baja.endswith(ext):
            peso = 70 if ext in (".apk", ".exe", ".msi", ".scr", ".jar") else 25
            _motivo(motivos, "descarga", peso,
                    f"La URL termina en {ext}: es una descarga directa.")
            break

    # Redireccion abierta: un dominio de confianza que reenvia a otro sitio.
    # Es "lavado de URL": el usuario ve google.com y acaba en el dominio malo.
    url_incrustada = None
    analisis_incrustado = None
    if partes_an.query:
        for clave, valores in parse_qs(partes_an.query).items():
            if clave.lower() not in PARAMS_REDIRECCION:
                continue
            for v in valores:
                v = unquote(v)
                if v.startswith("//"):
                    v = partes_an.scheme + ":" + v
                if v.startswith(("http://", "https://")):
                    url_incrustada = v
                    _motivo(motivos, "redireccion_abierta", 50,
                            f"El parametro '{clave}' reenvia a {v[:80]}.")
                    break
            if url_incrustada:
                break

    # Y se le pasa el mismo analisis a ese destino, en seco (sin red y sin
    # volver a anidar), para heredar sus senales: la marca suplantada suele
    # estar ahi, no en el dominio de la fachada.
    if url_incrustada and _profundidad == 0:
        interno = analizar_url(url_incrustada, whois_activo=False,
                               expandir_acortadores=False, _profundidad=1)
        analisis_incrustado = interno
        if interno["detalle"]["puntuacion"] >= 45:
            _motivo(motivos, "destino_incrustado_malo", 60,
                    "El destino al que reenvia ya es sospechoso por si solo "
                    f"({interno['detalle']['puntuacion']}/100).")
        if not typosquat and interno["es_typosquat"]:
            typosquat = True
            marca = interno["marca_suplantada"]
            tecnica = (interno["detalle"]["tecnica_typosquat"] or "") + \
                      " (en la URL incrustada)"

    # --- whois ----------------------------------------------------------
    info_whois: dict = {}
    edad = None
    if whois_activo and dominio and not es_ip and sufijo:
        info_whois = consultar_whois(dominio, timeout=max(timeout, 8.0))
        edad = info_whois.get("edad_dias")
        if edad is not None:
            if edad <= 7:
                _motivo(motivos, "dominio_recien_creado", 90,
                        f"Dominio registrado hace {edad} dias. Las campanas "
                        "de quishing usan dominios recien hechos.")
            elif edad <= 30:
                _motivo(motivos, "dominio_muy_nuevo", 75,
                        f"Dominio registrado hace {edad} dias.")
            elif edad <= 90:
                _motivo(motivos, "dominio_nuevo", 50,
                        f"Dominio registrado hace {edad} dias.")
            elif edad <= 365:
                _motivo(motivos, "dominio_reciente", 20,
                        f"Dominio registrado hace {edad} dias (menos de un ano).")
        # "Caduca pronto" solo dice algo en un dominio joven: significa que se
        # registro por el minimo de un ano y no piensan renovarlo. En uno
        # veterano es su renovacion anual de siempre (github.com caduca cada
        # ano y no tiene nada de raro), asi que ahi no cuenta.
        dias_caducar = info_whois.get("dias_para_caducar")
        if (dias_caducar is not None and 0 <= dias_caducar <= 60
                and edad is not None and edad <= 400):
            _motivo(motivos, "caduca_pronto", 20,
                    f"El dominio caduca en {dias_caducar} dias y solo tiene "
                    f"{edad} de vida: registro minimo, sin intencion de renovar.")

    # --- veredicto parcial ----------------------------------------------
    # El veredicto final lo compone el modulo 4; esto es solo la parte URL.
    puntuacion = _puntuar(motivos)

    return {
        # --- contrato ---
        "url": original,
        "edad_dominio_dias": edad,
        "tld_riesgo": tld_riesgo,
        "es_typosquat": typosquat,
        "marca_suplantada": marca,
        "es_acortador": acortador,
        "url_expandida": url_expandida,
        "deep_link": deep_link,
        # --- extra (no contractual, para el informe y el scoring) ---
        "detalle": {
            "url_analizada": url_analizada,
            "host": host_an,
            "host_legible": host_unicode,
            "dominio": dominio,
            "subdominio": subdominio,
            "sufijo": sufijo,
            "es_ip": es_ip,
            "esquema": partes_an.scheme,
            "tecnica_typosquat": tecnica,
            "url_incrustada": url_incrustada,
            "analisis_incrustado": analisis_incrustado,
            "cadena_redirecciones": cadena,
            "error_expansion": error_expansion,
            "whois": info_whois,
            "motivos": motivos,
            "puntuacion": puntuacion,
            "nivel": _nivel(puntuacion),
        },
    }


# =======================================================================
# CLI
# =======================================================================

def _informe_texto(r: dict) -> str:
    d = r["detalle"]
    lineas = [
        f"URL        : {r['url']}",
        f"Analizada  : {d['url_analizada']}",
        f"Dominio    : {d['dominio'] or '-'}   (TLD riesgo: {r['tld_riesgo']})",
        f"Edad       : {r['edad_dominio_dias'] if r['edad_dominio_dias'] is not None else 'desconocida'} dias",
        f"Typosquat  : {'SI -> ' + str(r['marca_suplantada']) if r['es_typosquat'] else 'no'}",
        f"Acortador  : {'si -> ' + str(r['url_expandida']) if r['es_acortador'] else 'no'}",
        f"Deep link  : {r['deep_link'] or 'no'}",
        f"Puntuacion : {d['puntuacion']}/100  ({d['nivel'].upper()})",
        "Motivos    :" if d["motivos"] else "Motivos    : ninguno",
    ]
    for m in d["motivos"]:
        lineas.append(f"  [{m['peso']:>2}] {m['texto']}")
    return "\n".join(lineas)


def _main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    banderas = {a for a in argv if a.startswith("--")}
    if not args:
        print(__doc__)
        return 1
    sin_red = "--sin-red" in banderas
    resultado = analizar_url(args[0],
                             whois_activo=not sin_red,
                             expandir_acortadores=not sin_red)
    if "--json" in banderas:
        print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    else:
        print(_informe_texto(resultado))
    return 0


if __name__ == "__main__":          # pragma: no cover
    # Ejecutar como modulo desde src/:  python -m qreaper.analisis_url <url>
    raise SystemExit(_main(sys.argv[1:]))
