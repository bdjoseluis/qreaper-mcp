"""
Módulo 3 — Sandbox de detonación  ·  Responsable: Jose

Abre la URL sospechosa en un Chromium headless y AISLADO para ver qué hace de
verdad: a dónde acaba llevando, si encadena redirecciones y si pide
credenciales. El usuario nunca abre el enlace: lo abrimos nosotros por él.

Hay DOS niveles de aislamiento y el resultado dice siempre cuál se ha usado
(clave ``aislamiento``):

  · ``"contenedor"`` — la detonación ocurre dentro de un contenedor Docker
    desechable, sin privilegios y con el sistema de archivos aislado. Es el
    modo bueno: si la web tumba el Chromium, se lleva por delante el
    contenedor, no la máquina.
  · ``"navegador"`` — Chromium en local con perfil desechable. Cubre el robo
    de sesión (no hay cookies que robar) pero NO un exploit del navegador.
    Es el modo de respaldo cuando no hay Docker.

Medidas de aislamiento comunes a los dos modos:
  · Perfil de navegador nuevo y desechable en cada análisis (sin cookies ni
    sesiones del usuario: aunque la web sea maliciosa, no hay nada que robar).
  · Descargas bloqueadas.
  · Permisos de cámara, micro, geolocalización y notificaciones denegados.
  · Solo se permite navegar por http/https: cualquier otro esquema
    (``file://``, ``telegram://``, ``intent://``...) se corta y se registra.
  · No se detonan destinos de la red interna (localhost, 192.168.x.x, ...):
    evita que un QR malicioso nos use para escanear la red de dentro.
  · Timeout duro: una web no puede dejarnos colgados.

Cómo elegir motor (variable de entorno ``QREAPER_SANDBOX``):
  ``auto`` (por defecto) usa Docker si la imagen está construida, y si no baja
  a local. ``docker`` obliga a contenedor y falla si no lo hay. ``local``
  obliga a Chromium en local.

Para construir la imagen:  ``python -m qreaper.sandbox --construir-imagen``
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

#: Dónde se guardan las capturas (carpeta ignorada por git).
#: Se puede mover con QREAPER_DIR_CAPTURAS (el contenedor la apunta a /salidas).
DIR_CAPTURAS = Path(os.environ.get("QREAPER_DIR_CAPTURAS", "datasets/tmp"))

#: Tiempo máximo esperando a que cargue una página.
TIMEOUT_MS = 20_000

#: Nos hacemos pasar por un Chrome normal: muchas webs de phishing esconden el
#: contenido si detectan que las está mirando un robot.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

ESQUEMAS_PERMITIDOS = {"http", "https"}

#: Pistas de que un formulario busca credenciales aunque no use type=password.
PISTAS_LOGIN = (
    "contraseña", "contrasena", "password", "passwd", "clave", "pin",
    "usuario", "iniciar sesión", "iniciar sesion", "acceder", "login",
    "sign in", "log in",
)

# --------------------------------------------------------------------------
# Configuración del motor
# --------------------------------------------------------------------------

#: Nombre de la imagen del sandbox.
IMAGEN_DOCKER = os.environ.get("QREAPER_IMAGEN", "qreaper-sandbox:latest")

#: ``auto`` | ``docker`` | ``local``
MOTOR_POR_DEFECTO = os.environ.get("QREAPER_SANDBOX", "auto").lower()

#: True cuando este código ya se está ejecutando DENTRO del contenedor.
#: Sirve para no intentar lanzar Docker dentro de Docker y para pasarle a
#: Chromium el ``--no-sandbox`` que necesita cuando le quitamos capabilities.
EN_CONTENEDOR = os.environ.get("QREAPER_EN_CONTENEDOR") == "1"

#: Escotilla de escape para los que quieran probar contra un lab en localhost.
PERMITIR_RED_PRIVADA = os.environ.get("QREAPER_PERMITIR_RED_PRIVADA") == "1"

#: Raíz del repo (para encontrar el Dockerfile desde donde sea).
_RAIZ = Path(__file__).resolve().parent.parent.parent

_docker_ok: bool | None = None       # caché: ¿hay demonio de Docker?
_imagen_ok: bool | None = None       # caché: ¿está construida la imagen?


def _ruta_captura(url: str) -> Path:
    """Nombre de archivo único y sin caracteres raros para la captura."""
    hueco = hashlib.sha1(url.encode("utf-8", "ignore")).hexdigest()[:10]
    DIR_CAPTURAS.mkdir(parents=True, exist_ok=True)
    return DIR_CAPTURAS / f"shot_{int(time.time())}_{hueco}.png"


def _resultado_vacio(url: str, error: str, aislamiento: str = "ninguno") -> dict:
    """Respuesta cuando no hemos podido detonar. Respeta el contrato igual."""
    return {
        "url_final": url,
        "cadena_redirecciones": [url],
        "screenshot_path": None,
        "hay_formulario_login": False,
        "error": error,
        "aislamiento": aislamiento,
    }


def _motivo_red_privada(url: str) -> str | None:
    """¿La URL apunta a la red interna? Devuelve el motivo, o None si es pública.

    Un QR malicioso podría apuntar a ``http://192.168.1.1/`` para usar nuestro
    sandbox como trampolín hacia la red de dentro (el clásico SSRF). Como el
    contenedor sí tiene salida a internet, esto hay que cortarlo aquí.
    """
    if PERMITIR_RED_PRIVADA:
        return None

    host = urlparse(url).hostname
    if not host:
        return None

    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        # No resuelve: no es cosa nuestra, que lo reporte Playwright.
        return None

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified
        ):
            return (
                f"No se detona '{host}' porque apunta a la red interna ({ip}). "
                "Si es un laboratorio propio: QREAPER_PERMITIR_RED_PRIVADA=1"
            )
    return None


def _detectar_login(page) -> bool:
    """¿La página pide credenciales? Mira el documento y todos los iframes."""
    for frame in page.frames:
        try:
            if frame.query_selector("input[type='password']"):
                return True
            # Formularios que piden la contraseña sin usar type=password
            # (truco habitual para saltarse los detectores automáticos).
            for form in frame.query_selector_all("form"):
                texto = (form.inner_text() or "").lower()
                if any(p in texto for p in PISTAS_LOGIN) and form.query_selector("input"):
                    return True
        except Exception:
            # Un iframe de otro dominio puede negarnos el acceso: no es un fallo
            # del análisis, seguimos con el resto.
            continue
    return False


# --------------------------------------------------------------------------
# Motor 1: Chromium en local
# --------------------------------------------------------------------------

def detonar_local(url: str, *, timeout_ms: int = TIMEOUT_MS, captura: bool = True) -> dict:
    """Detona con Chromium en ESTA máquina (perfil desechable, sin Docker).

    Es el motor de respaldo y también el que corre dentro del contenedor.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _resultado_vacio(
            url,
            "Playwright no está instalado. Ejecuta: "
            "pip install playwright && playwright install chromium",
        )

    esquema = url.split(":", 1)[0].lower() if ":" in url else ""
    if esquema not in ESQUEMAS_PERMITIDOS:
        return _resultado_vacio(
            url, f"No se detona el esquema '{esquema}': no es una web (http/https)"
        )

    motivo = _motivo_red_privada(url)
    if motivo:
        return _resultado_vacio(url, motivo)

    aislamiento = "contenedor" if EN_CONTENEDOR else "navegador"
    cadena: list[str] = []
    ruta_captura = None
    error = None
    url_final = url

    # Dentro del contenedor le quitamos todas las capabilities al proceso, así
    # que el sandbox propio de Chromium no puede arrancar: el aislamiento lo
    # pone el contenedor, no el navegador.
    args_navegador = ["--no-sandbox", "--disable-dev-shm-usage"] if EN_CONTENEDOR else []

    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=True, args=args_navegador)
            contexto = navegador.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1366, "height": 768},
                locale="es-ES",
                ignore_https_errors=True,   # los sitios de phishing suelen tener certificados rotos
                accept_downloads=False,
                java_script_enabled=True,
            )
            contexto.clear_permissions()
            contexto.set_default_timeout(timeout_ms)

            page = contexto.new_page()

            # Cada navegación del marco principal es un eslabón de la cadena:
            # así capturamos tanto los 301/302 como los saltos por JavaScript.
            def _apuntar(frame):
                if frame is page.main_frame and frame.url not in ("about:blank", ""):
                    if not cadena or cadena[-1] != frame.url:
                        cadena.append(frame.url)

            page.on("framenavigated", _apuntar)

            try:
                respuesta = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                # Los saltos HTTP (301/302) ocurren ANTES de que el navegador
                # aterrice, así que 'framenavigated' no los ve. Hay que
                # reconstruirlos hacia atrás desde la petición final: es
                # exactamente lo que hace un acortador tipo bit.ly.
                if respuesta is not None:
                    saltos_http, peticion = [], respuesta.request
                    while peticion is not None:
                        saltos_http.append(peticion.url)
                        peticion = peticion.redirected_from
                    saltos_http.reverse()   # del primero al último
                    # Los saltos HTTP van SIEMPRE delante de lo que ya haya
                    # apuntado el listener (que es el destino y sus saltos JS).
                    cadena[:] = [u for u in saltos_http if u not in cadena] + cadena
                # Margen para redirecciones por JS o meta-refresh.
                page.wait_for_timeout(1500)
            except Exception as e:
                error = f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"

            url_final = page.url or url
            hay_login = _detectar_login(page) if not error or page.url != "about:blank" else False

            if captura:
                try:
                    ruta_captura = str(_ruta_captura(url))
                    page.screenshot(path=ruta_captura, full_page=False)
                except Exception:
                    ruta_captura = None

            contexto.close()
            navegador.close()

    except Exception as e:
        return _resultado_vacio(
            url, f"{type(e).__name__}: {str(e).splitlines()[0][:200]}", aislamiento
        )

    if not cadena:
        cadena = [url]
    if cadena[-1] != url_final:
        cadena.append(url_final)

    return {
        "url_final": url_final,
        "cadena_redirecciones": cadena,
        "screenshot_path": ruta_captura,
        "hay_formulario_login": hay_login,
        "error": error,
        "aislamiento": aislamiento,
    }


# --------------------------------------------------------------------------
# Motor 2: contenedor Docker
# --------------------------------------------------------------------------

def _docker(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Llama al cliente de docker sin abrir ventana ni heredar stdin."""
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )


def hay_docker(refrescar: bool = False) -> bool:
    """¿Está el demonio de Docker vivo? (se cachea, la comprobación es lenta)"""
    global _docker_ok
    if _docker_ok is None or refrescar:
        try:
            _docker_ok = _docker("info", "--format", "{{.ServerVersion}}", timeout=20).returncode == 0
        except (OSError, subprocess.SubprocessError):
            _docker_ok = False
    return _docker_ok


def hay_imagen(refrescar: bool = False) -> bool:
    """¿Está construida la imagen del sandbox?"""
    global _imagen_ok
    if _imagen_ok is None or refrescar:
        if not hay_docker():
            _imagen_ok = False
        else:
            try:
                _imagen_ok = _docker("image", "inspect", IMAGEN_DOCKER, timeout=30).returncode == 0
            except (OSError, subprocess.SubprocessError):
                _imagen_ok = False
    return _imagen_ok


def construir_imagen(mostrar: bool = True) -> bool:
    """Construye la imagen del sandbox. Devuelve True si ha ido bien."""
    global _imagen_ok
    if not hay_docker(refrescar=True):
        if mostrar:
            print("No hay demonio de Docker. Arranca Docker Desktop y repite.")
        return False

    dockerfile = _RAIZ / "docker" / "Dockerfile.sandbox"
    if not dockerfile.exists():
        if mostrar:
            print(f"No encuentro {dockerfile}")
        return False

    if mostrar:
        print(f"Construyendo {IMAGEN_DOCKER}... (la primera vez tarda, baja ~2 GB)")
    proceso = _docker(
        "build", "-f", str(dockerfile), "-t", IMAGEN_DOCKER, str(_RAIZ),
        timeout=1800,
    )
    _imagen_ok = proceso.returncode == 0
    if mostrar:
        print("Imagen lista." if _imagen_ok else f"Ha fallado:\n{proceso.stderr[-2000:]}")
    return _imagen_ok


def detonar_en_docker(url: str, *, timeout_ms: int = TIMEOUT_MS, captura: bool = True) -> dict:
    """Detona la URL dentro de un contenedor desechable.

    El contenedor va sin privilegios, sin capabilities, con memoria y procesos
    topados y se destruye al terminar (``--rm``). Lo único que comparte con la
    máquina es la carpeta de capturas.
    """
    if not hay_docker():
        return _resultado_vacio(url, "No hay demonio de Docker en marcha")
    if not hay_imagen():
        return _resultado_vacio(
            url,
            f"Falta la imagen {IMAGEN_DOCKER}. Constrúyela con: "
            "python -m qreaper.sandbox --construir-imagen",
        )

    dir_capturas = DIR_CAPTURAS.resolve()
    dir_capturas.mkdir(parents=True, exist_ok=True)

    orden = [
        "run", "--rm",
        "--user", "pwuser",
        "--cap-drop", "ALL",                    # sin capabilities de root
        "--security-opt", "no-new-privileges",  # no puede escalar
        "--memory", "1g",                       # una bomba de memoria no tumba el PC
        "--pids-limit", "512",                  # ni una fork bomb
        "--shm-size", "1g",                     # Chromium necesita /dev/shm grande
        "-e", "QREAPER_DIR_CAPTURAS=/salidas",
        "-v", f"{dir_capturas}:/salidas",
        IMAGEN_DOCKER,
        url, "--timeout", str(timeout_ms),
    ]
    if not captura:
        orden.append("--sin-captura")

    # Margen generoso por encima del timeout de página: arrancar el contenedor
    # y Chromium también cuesta.
    limite = timeout_ms / 1000 + 60

    try:
        proceso = _docker(*orden, timeout=limite)
    except subprocess.TimeoutExpired:
        return _resultado_vacio(url, f"El contenedor no respondió en {limite:.0f}s", "contenedor")
    except (OSError, subprocess.SubprocessError) as e:
        return _resultado_vacio(url, f"{type(e).__name__}: {e}", "contenedor")

    if proceso.returncode != 0:
        detalle = (proceso.stderr or proceso.stdout or "").strip().splitlines()
        return _resultado_vacio(
            url,
            f"El contenedor salió con código {proceso.returncode}: "
            f"{detalle[-1][:200] if detalle else 'sin salida'}",
            "contenedor",
        )

    # El contenedor imprime el JSON del resultado. Nos quedamos con el último
    # bloque {...} por si Playwright ha escupido algún aviso por delante.
    salida = proceso.stdout or ""
    inicio = salida.find("{")
    if inicio == -1:
        return _resultado_vacio(url, "El contenedor no devolvió JSON", "contenedor")
    try:
        resultado = json.loads(salida[inicio:])
    except json.JSONDecodeError as e:
        return _resultado_vacio(url, f"JSON ilegible del contenedor: {e}", "contenedor")

    # La captura la ha escrito en /salidas, que por fuera es DIR_CAPTURAS.
    ruta = resultado.get("screenshot_path")
    if ruta:
        resultado["screenshot_path"] = str(DIR_CAPTURAS / Path(ruta).name)

    resultado["aislamiento"] = "contenedor"
    return resultado


# --------------------------------------------------------------------------
# Punto de entrada del contrato
# --------------------------------------------------------------------------

def detonar(
    url: str,
    *,
    timeout_ms: int = TIMEOUT_MS,
    captura: bool = True,
    motor: str | None = None,
) -> dict:
    """Abre la URL en un navegador headless aislado y recoge evidencias.

    Args:
        url: la dirección a detonar (normalmente sacada de un QR).
        timeout_ms: tiempo máximo de carga antes de rendirse.
        captura: si False, no hace screenshot (más rápido para lotes).
        motor: ``"auto"`` | ``"docker"`` | ``"local"``. Por defecto, lo que
            diga la variable de entorno ``QREAPER_SANDBOX`` (``auto``).

    Returns:
        dict con ``url_final``, ``cadena_redirecciones``, ``screenshot_path``,
        ``hay_formulario_login``, ``error`` (None si todo fue bien) y
        ``aislamiento`` (``"contenedor"`` | ``"navegador"``).
    """
    motor = (motor or MOTOR_POR_DEFECTO).lower()

    if EN_CONTENEDOR:
        # Ya estamos dentro: no hay Docker dentro de Docker.
        return detonar_local(url, timeout_ms=timeout_ms, captura=captura)

    if motor == "local":
        return detonar_local(url, timeout_ms=timeout_ms, captura=captura)

    if motor == "docker":
        return detonar_en_docker(url, timeout_ms=timeout_ms, captura=captura)

    # auto: contenedor si está listo, si no local.
    if hay_imagen():
        return detonar_en_docker(url, timeout_ms=timeout_ms, captura=captura)
    return detonar_local(url, timeout_ms=timeout_ms, captura=captura)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="python -m qreaper.sandbox",
        description="Detona una URL en el sandbox y escupe el JSON del resultado.",
    )
    parser.add_argument("url", nargs="?", help="URL a detonar")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_MS, help="ms de espera")
    parser.add_argument("--sin-captura", action="store_true", help="no hacer screenshot")
    parser.add_argument("--motor", choices=["auto", "docker", "local"], default=None)
    parser.add_argument(
        "--construir-imagen", action="store_true",
        help="construye la imagen Docker del sandbox y sale",
    )
    args = parser.parse_args()

    if args.construir_imagen:
        raise SystemExit(0 if construir_imagen() else 1)

    if not args.url:
        parser.error("hace falta una URL (o --construir-imagen)")

    resultado = detonar(
        args.url,
        timeout_ms=args.timeout,
        captura=not args.sin_captura,
        motor=args.motor,
    )
    json.dump(resultado, sys.stdout, indent=2, ensure_ascii=False)
    print()
