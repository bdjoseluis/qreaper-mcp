"""
Módulo 3 — Sandbox de detonación  ·  Responsable: Jose

Abre la URL sospechosa en un Chromium headless y AISLADO para ver qué hace de
verdad: a dónde acaba llevando, si encadena redirecciones y si pide
credenciales. El usuario nunca abre el enlace: lo abrimos nosotros por él.

Medidas de aislamiento (importante para la memoria del proyecto):
  · Perfil de navegador nuevo y desechable en cada análisis (sin cookies ni
    sesiones del usuario: aunque la web sea maliciosa, no hay nada que robar).
  · Descargas bloqueadas.
  · Permisos de cámara, micro, geolocalización y notificaciones denegados.
  · Solo se permite navegar por http/https: cualquier otro esquema
    (``file://``, ``telegram://``, ``intent://``...) se corta y se registra.
  · Timeout duro: una web no puede dejarnos colgados.

PENDIENTE: meter esto dentro de un contenedor Docker para aislarlo también del
sistema operativo. Hoy el aislamiento es a nivel de navegador, que cubre el
robo de sesión pero no un exploit del propio Chromium.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

#: Dónde se guardan las capturas (carpeta ignorada por git).
DIR_CAPTURAS = Path("datasets/tmp")

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


def _ruta_captura(url: str) -> Path:
    """Nombre de archivo único y sin caracteres raros para la captura."""
    hueco = hashlib.sha1(url.encode("utf-8", "ignore")).hexdigest()[:10]
    DIR_CAPTURAS.mkdir(parents=True, exist_ok=True)
    return DIR_CAPTURAS / f"shot_{int(time.time())}_{hueco}.png"


def _resultado_vacio(url: str, error: str) -> dict:
    """Respuesta cuando no hemos podido detonar. Respeta el contrato igual."""
    return {
        "url_final": url,
        "cadena_redirecciones": [url],
        "screenshot_path": None,
        "hay_formulario_login": False,
        "error": error,
    }


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


def detonar(url: str, *, timeout_ms: int = TIMEOUT_MS, captura: bool = True) -> dict:
    """Abre la URL en un navegador headless aislado y recoge evidencias.

    Args:
        url: la dirección a detonar (normalmente sacada de un QR).
        timeout_ms: tiempo máximo de carga antes de rendirse.
        captura: si False, no hace screenshot (más rápido para lotes).

    Returns:
        dict con ``url_final``, ``cadena_redirecciones``, ``screenshot_path``,
        ``hay_formulario_login`` y ``error`` (None si todo fue bien).
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

    cadena: list[str] = []
    ruta_captura = None
    error = None
    url_final = url

    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=True)
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
        return _resultado_vacio(url, f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")

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
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Uso: python -m qreaper.sandbox <url>")
        raise SystemExit(1)
    print(json.dumps(detonar(sys.argv[1]), indent=2, ensure_ascii=False))
