"""
Módulo 5 — Informe  ·  Responsable: JuanFran

Convierte el resultado completo del análisis (url + señales + sandbox +
scoring) en un informe legible por una persona: JSON, HTML o PDF.

Dos reglas que sigue este módulo:

1. **Nunca da por hecho que los demás módulos están terminados.** Si faltan
   señales o el sandbox no llegó a detonar, se escribe "sin datos" y el
   informe se genera igual. El informe es justo lo que el usuario mira
   cuando algo ha ido mal, así que es el peor sitio para reventar.
2. **JSON y HTML no necesitan ninguna dependencia externa.** Solo el PDF usa
   ``reportlab`` (declarado en ``requirements.txt``), y se importa dentro de
   la función para que los otros dos formatos funcionen aunque no esté.
"""
from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

#: Formatos que acepta ``generar_informe()``.
FORMATOS = ("json", "html", "pdf")

#: Color con el que se pinta el veredicto en HTML y PDF.
COLOR_VEREDICTO = {
    "PELIGRO": "#b3261e",
    "SOSPECHOSO": "#b26a00",
    "SEGURO": "#1e6b3a",
    "DESCONOCIDO": "#5f6368",
}

#: Qué debe hacer la persona que ha escaneado el QR, en lenguaje llano.
RECOMENDACION = {
    "PELIGRO": (
        "No abras el enlace ni introduzcas ningún dato. Si ya lo has hecho, "
        "cambia inmediatamente la contraseña afectada y avisa al responsable "
        "de sistemas de tu organización."
    ),
    "SOSPECHOSO": (
        "Trátalo como no fiable: no introduzcas credenciales ni datos de pago. "
        "Confirma por otro canal (teléfono conocido, web oficial escrita a "
        "mano) que quien lo envía es quien dice ser."
    ),
    "SEGURO": (
        "No se han detectado indicios de fraude. Aun así, comprueba siempre la "
        "dirección que aparece en la barra del navegador antes de escribir una "
        "contraseña."
    ),
    "DESCONOCIDO": (
        "No ha sido posible completar el análisis, así que este informe no "
        "confirma que el enlace sea seguro. Trátalo como no verificado hasta "
        "poder repetir el análisis."
    ),
}

#: Nombre humano de cada señal de ``analisis_url`` (ver CONTRATOS.md).
ETIQUETAS_SENALES = {
    "edad_dominio_dias": "Edad del dominio (días)",
    "tld_riesgo": "Riesgo de la extensión del dominio",
    "es_typosquat": "Imita a una marca conocida",
    "marca_suplantada": "Marca suplantada",
    "es_acortador": "Es un acortador de enlaces",
    "url_expandida": "Dirección real tras expandir",
    "deep_link": "Abre una aplicación (deep link)",
}

#: Nombre humano de cada dato de ``sandbox.detonar()``.
ETIQUETAS_SANDBOX = {
    "url_final": "Dirección final tras las redirecciones",
    "hay_formulario_login": "La página pide usuario y contraseña",
    "aislamiento": "Aislamiento usado en la detonación",
    "error": "Incidencia durante la detonación",
}


def generar_informe(resultado: dict, formato: str = "pdf", destino: str | None = None) -> str:
    """Genera el informe y devuelve la ruta del archivo.

    Args:
        resultado: el diccionario que arma ``pipeline.analizar_url_suelta()``
            (claves ``url``, ``senales``, ``sandbox``, ``scoring``, ``errores``).
            Se tolera que vengan a medias o que falten.
        formato: ``"pdf"`` | ``"json"`` | ``"html"``.
        destino: ruta concreta donde escribir. Si no se indica, se genera un
            nombre con el dominio y la fecha en el directorio actual.

    Returns:
        La ruta del archivo generado, como cadena.

    Raises:
        ValueError: si el formato no es uno de los tres soportados.
        RuntimeError: si se pide PDF y ``reportlab`` no está instalado.
    """
    formato = str(formato or "pdf").strip().lower().lstrip(".")
    if formato not in FORMATOS:
        raise ValueError(
            f"Formato '{formato}' no soportado. Usa uno de: {', '.join(FORMATOS)}"
        )

    datos = _resumen(resultado)
    ruta = _ruta_de_salida(destino, datos["url"], formato)

    if formato == "json":
        _escribir_json(resultado, datos, ruta)
    elif formato == "html":
        _escribir_html(datos, ruta)
    else:
        _escribir_pdf(datos, ruta)

    return str(ruta)


# --------------------------------------------------------------- preparación

def _resumen(resultado: dict) -> dict:
    """Normaliza el resultado del pipeline a lo que necesitan las plantillas.

    Aquí es donde se absorbe que un módulo esté a medias: todo se lee con
    ``.get()`` y cualquier hueco acaba en "sin datos".
    """
    resultado = resultado or {}
    scoring = resultado.get("scoring") or {}
    sandbox = resultado.get("sandbox") or {}
    senales = resultado.get("senales") or {}

    veredicto = str(scoring.get("veredicto") or "DESCONOCIDO").upper()
    if veredicto not in RECOMENDACION:
        veredicto = "DESCONOCIDO"

    nota = scoring.get("nota")

    return {
        "url": resultado.get("url") or senales.get("url") or "sin datos",
        "fecha": datetime.now().strftime("%d/%m/%Y a las %H:%M"),
        "veredicto": veredicto,
        "nota": "sin datos" if nota is None else f"{nota}/100",
        "color": COLOR_VEREDICTO[veredicto],
        "recomendacion": RECOMENDACION[veredicto],
        "motivos": list(scoring.get("motivos") or []),
        "detalle": list(scoring.get("detalle") or []),
        "senales": _filas(senales, ETIQUETAS_SENALES),
        "sandbox": _filas(sandbox, ETIQUETAS_SANDBOX),
        "redirecciones": list(sandbox.get("cadena_redirecciones") or []),
        "screenshot": sandbox.get("screenshot_path"),
        "errores": resultado.get("errores") or {},
    }


def _filas(origen: dict, etiquetas: dict) -> list[tuple[str, str]]:
    """Pasa un diccionario a filas ``(etiqueta, valor legible)``.

    Solo salen las claves que vienen de verdad: si ``analisis_url`` todavía no
    devuelve ``marca_suplantada``, esa fila no aparece en vez de mentir con un
    "no".
    """
    return [
        (etiquetas[clave], _texto(origen[clave]))
        for clave in etiquetas
        if clave in origen and origen[clave] not in (None, "")
    ]


def _mezcla_con_blanco(color_hex: str, proporcion: float) -> tuple[float, float, float]:
    """Versión clarita de un color, en componentes 0-1.

    Hace falta porque reportlab no entiende los hex de 8 dígitos con alfa que
    sí valen en CSS: ``HexColor("#b3261e18")`` no da un rojo transparente, da
    un color equivocado. Así que el "fondo suave" se calcula mezclando con
    blanco a mano.
    """
    color_hex = color_hex.lstrip("#")
    canales = (int(color_hex[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(c * proporcion + (1 - proporcion) for c in canales)  # type: ignore[return-value]


def _texto(valor) -> str:
    """Cualquier valor -> algo que se pueda imprimir sin que chirríe."""
    if valor is None or valor == "":
        return "sin datos"
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    if isinstance(valor, (list, tuple)):
        return ", ".join(_texto(v) for v in valor) if valor else "sin datos"
    return str(valor)


def _ruta_de_salida(destino: str | None, url: str, formato: str) -> Path:
    """Decide dónde se escribe y se asegura de que la carpeta existe."""
    if destino:
        ruta = Path(destino)
        # Si nos dan "informes/analisis" sin extensión, se la ponemos nosotros.
        if not ruta.suffix:
            ruta = ruta.with_suffix(f".{formato}")
    else:
        host = urlparse(url).hostname or "informe"
        host = re.sub(r"[^A-Za-z0-9.-]", "_", host)[:40]
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        ruta = Path(f"informe_{host}_{marca}.{formato}")

    if str(ruta.parent) not in ("", "."):
        ruta.parent.mkdir(parents=True, exist_ok=True)
    return ruta


# ---------------------------------------------------------------------- JSON

def _escribir_json(resultado: dict, datos: dict, ruta: Path) -> None:
    """Vuelca el análisis entero + la lectura humana. Es el formato para máquinas.

    ``default=str`` es la red de seguridad: si algún módulo mete un objeto raro
    (una fecha de whois, por ejemplo), se serializa como texto en vez de tumbar
    el informe.
    """
    contenido = {
        "herramienta": "QReaper",
        "generado_en": datetime.now().isoformat(timespec="seconds"),
        "veredicto": datos["veredicto"],
        "recomendacion": datos["recomendacion"],
        "analisis": resultado,
    }
    ruta.write_text(
        json.dumps(contenido, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------- HTML

_CSS = """
* { box-sizing: border-box; }
body { margin: 0; padding: 32px 20px; background: #f2f3f5;
       font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       color: #1c1c1e; line-height: 1.5; }
.hoja { max-width: 860px; margin: 0 auto; background: #fff; border-radius: 14px;
        box-shadow: 0 2px 16px rgba(0,0,0,.09); overflow: hidden; }
header { background: #16181d; color: #fff; padding: 26px 32px; }
header h1 { margin: 0; font-size: 20px; letter-spacing: .02em; }
header p { margin: 6px 0 0; font-size: 13px; color: #a5abb6; }
.cuerpo { padding: 28px 32px 36px; }
.veredicto { display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
             padding: 18px 20px; border-radius: 10px; margin-bottom: 26px; }
.chapa { font-size: 20px; font-weight: 700; letter-spacing: .06em; }
.nota { font-size: 14px; opacity: .85; }
.url { font-family: ui-monospace, Consolas, monospace; font-size: 13px;
       word-break: break-all; background: #f4f4f6; border: 1px solid #e3e3e8;
       border-radius: 8px; padding: 10px 12px; margin-bottom: 26px; }
h2 { font-size: 14px; text-transform: uppercase; letter-spacing: .08em;
     color: #6b7280; margin: 30px 0 12px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
td { padding: 9px 4px; border-bottom: 1px solid #ececf1; vertical-align: top; }
td.clave { color: #55596b; width: 46%; }
td.valor { font-weight: 600; word-break: break-word; }
ul { margin: 0; padding-left: 20px; font-size: 14px; }
li { margin-bottom: 6px; }
.consejo { border-left: 4px solid currentColor; padding: 14px 18px;
           border-radius: 0 8px 8px 0; font-size: 14px; }
.aviso { background: #fff8e6; border: 1px solid #f0dca8; border-radius: 8px;
         padding: 12px 16px; font-size: 13px; color: #6b5310; }
img.captura { width: 100%; border: 1px solid #dcdce3; border-radius: 8px; }
footer { padding: 18px 32px 26px; font-size: 12px; color: #8a8f9c; }
@media print { body { background: #fff; padding: 0; }
               .hoja { box-shadow: none; border-radius: 0; } }
"""


def _escribir_html(datos: dict, ruta: Path) -> None:
    """Informe autocontenido: un solo archivo, sin CSS ni imágenes externas."""
    e = html.escape
    partes: list[str] = []

    partes.append(f"""<div class="veredicto" style="background:{datos['color']}18;color:{datos['color']}">
      <span class="chapa">{e(datos['veredicto'])}</span>
      <span class="nota">Nivel de riesgo: {e(datos['nota'])}</span>
    </div>
    <h2>Dirección analizada</h2>
    <div class="url">{e(datos['url'])}</div>""")

    if datos["motivos"]:
        filas = "".join(f"<li>{e(_texto(m))}</li>" for m in datos["motivos"])
        partes.append(f"<h2>Por qué</h2><ul>{filas}</ul>")

    partes.append(
        f'<h2>Qué hacer</h2><div class="consejo" style="color:{datos["color"]}">'
        f'<span style="color:#1c1c1e">{e(datos["recomendacion"])}</span></div>'
    )

    partes.append(_tabla_html("Señales de la dirección", datos["senales"]))
    partes.append(_tabla_html("Detonación en el sandbox", datos["sandbox"]))

    if len(datos["redirecciones"]) > 1:
        saltos = "".join(f"<li>{e(_texto(u))}</li>" for u in datos["redirecciones"])
        partes.append(f"<h2>Cadena de redirecciones</h2><ul>{saltos}</ul>")

    if datos["detalle"]:
        filas = "".join(
            f'<tr><td class="clave">{e(_texto(d.get("motivo")))}</td>'
            f'<td class="valor">+{e(_texto(d.get("puntos")))}</td></tr>'
            for d in datos["detalle"]
        )
        partes.append(f"<h2>Desglose de la puntuación</h2><table>{filas}</table>")

    captura = _imagen_incrustada(datos["screenshot"])
    if captura:
        partes.append(
            f'<h2>Captura de la página</h2><img class="captura" alt="Captura de '
            f'la página analizada" src="{captura}">'
        )

    if datos["errores"]:
        fallos = "".join(
            f"<li><strong>{e(str(k))}</strong>: {e(str(v))}</li>"
            for k, v in datos["errores"].items()
        )
        partes.append(
            f'<h2>Limitaciones de este análisis</h2><div class="aviso">'
            f"Estas partes del análisis no se han podido completar:<ul>{fallos}</ul></div>"
        )

    documento = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QReaper — informe de {e(datos['url'])}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="hoja">
  <header>
    <h1>QReaper · Informe de análisis anti-quishing</h1>
    <p>Generado el {e(datos['fecha'])}</p>
  </header>
  <div class="cuerpo">
    {"".join(partes)}
  </div>
  <footer>
    Informe automático. La dirección se ha abierto en un entorno aislado; en
    ningún momento se ha visitado desde este equipo.
  </footer>
</div>
</body>
</html>
"""
    ruta.write_text(documento, encoding="utf-8")


def _tabla_html(titulo: str, filas: list[tuple[str, str]]) -> str:
    """Tabla de dos columnas, o cadena vacía si no hay nada que enseñar."""
    if not filas:
        return ""
    e = html.escape
    cuerpo = "".join(
        f'<tr><td class="clave">{e(clave)}</td><td class="valor">{e(valor)}</td></tr>'
        for clave, valor in filas
    )
    return f"<h2>{e(titulo)}</h2><table>{cuerpo}</table>"


def _imagen_incrustada(ruta_captura) -> str | None:
    """La captura como data-URI, para que el HTML sea un archivo suelto.

    Devuelve None (y el informe se genera sin imagen) si no hay captura, si el
    sandbox no llegó a hacerla o si el archivo ya no está.
    """
    if not ruta_captura:
        return None
    archivo = Path(ruta_captura)
    if not archivo.is_file():
        return None
    try:
        crudo = archivo.read_bytes()
    except OSError:
        return None
    mime = mimetypes.guess_type(archivo.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(crudo).decode('ascii')}"


# ----------------------------------------------------------------------- PDF

def _escribir_pdf(datos: dict, ruta: Path) -> None:
    """Informe en PDF con reportlab. Es el formato para enviar por correo."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import (
            Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError as fallo:
        raise RuntimeError(
            "Para generar el informe en PDF hace falta reportlab. "
            "Instálalo con:  pip install reportlab   "
            "(o pide el informe en formato 'html', que no necesita nada)."
        ) from fallo

    color = colors.HexColor(datos["color"])
    hojas = getSampleStyleSheet()

    normal = ParagraphStyle(
        "cuerpo", parent=hojas["Normal"], fontName="Helvetica",
        fontSize=9.5, leading=13.5, alignment=TA_LEFT,
        # wordWrap CJK parte también las palabras larguísimas: sin esto, una
        # URL de 200 caracteres se sale de la celda.
        wordWrap="CJK",
    )
    apartado = ParagraphStyle(
        "apartado", parent=normal, fontName="Helvetica-Bold", fontSize=9,
        textColor=colors.HexColor("#6b7280"), spaceBefore=14, spaceAfter=5,
    )
    monoespacio = ParagraphStyle(
        "url", parent=normal, fontName="Courier", fontSize=9, leading=12,
    )

    def parrafo(texto: str, estilo=normal):
        return Paragraph(html.escape(_texto(texto)), estilo)

    historia: list = []

    # --- cabecera
    historia.append(Paragraph(
        "QReaper &middot; Informe de análisis anti-quishing",
        ParagraphStyle("titulo", parent=normal, fontName="Helvetica-Bold",
                       fontSize=15, leading=19, spaceAfter=2),
    ))
    historia.append(Paragraph(
        f"Generado el {html.escape(datos['fecha'])}",
        ParagraphStyle("fecha", parent=normal, fontSize=8.5,
                       textColor=colors.HexColor("#8a8f9c"), spaceAfter=14),
    ))

    # --- chapa del veredicto
    chapa = Table(
        [[Paragraph(
            f'<font size="14"><b>{html.escape(datos["veredicto"])}</b></font>'
            f'<br/><font size="9">Nivel de riesgo: '
            f'{html.escape(datos["nota"])}</font>',
            ParagraphStyle("chapa", parent=normal, textColor=color, leading=18),
        )]],
        colWidths=[165 * mm],
    )
    chapa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*_mezcla_con_blanco(datos["color"], 0.10))),
        ("BOX", (0, 0), (-1, -1), 0.8, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    historia.append(chapa)

    historia.append(Paragraph("DIRECCIÓN ANALIZADA", apartado))
    historia.append(parrafo(datos["url"], monoespacio))

    if datos["motivos"]:
        # La viñeta va por bulletText, no dentro del texto: el contenido se
        # escapa y un "&bull;" saldría escrito tal cual.
        vineta = ParagraphStyle("vineta", parent=normal, leftIndent=12, spaceAfter=3)
        historia.append(Paragraph("POR QUÉ", apartado))
        for motivo in datos["motivos"]:
            historia.append(
                Paragraph(html.escape(_texto(motivo)), vineta, bulletText="•")
            )

    historia.append(Paragraph("QUÉ HACER", apartado))
    consejo = Table([[parrafo(datos["recomendacion"])]], colWidths=[165 * mm])
    consejo.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    historia.append(consejo)

    def bloque(titulo: str, filas: list[tuple[str, str]]) -> None:
        """Añade un apartado con su tabla de dos columnas, si hay filas."""
        if not filas:
            return
        historia.append(Paragraph(titulo, apartado))
        tabla = Table(
            [[parrafo(clave), parrafo(valor)] for clave, valor in filas],
            colWidths=[75 * mm, 90 * mm],
        )
        tabla.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#ececf1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#55596b")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ]))
        historia.append(tabla)

    bloque("SEÑALES DE LA DIRECCIÓN", datos["senales"])
    bloque("DETONACIÓN EN EL SANDBOX", datos["sandbox"])

    if len(datos["redirecciones"]) > 1:
        historia.append(Paragraph("CADENA DE REDIRECCIONES", apartado))
        for salto, destino_salto in enumerate(datos["redirecciones"], start=1):
            historia.append(parrafo(f"{salto}. {_texto(destino_salto)}", monoespacio))

    bloque(
        "DESGLOSE DE LA PUNTUACIÓN",
        [(_texto(d.get("motivo")), f"+{_texto(d.get('puntos'))}") for d in datos["detalle"]],
    )

    if datos["errores"]:
        bloque(
            "LIMITACIONES DE ESTE ANÁLISIS",
            [(str(k), str(v)) for k, v in datos["errores"].items()],
        )

    imagen = _imagen_para_pdf(datos["screenshot"], Image, ImageReader, mm)
    if imagen is not None:
        historia.append(PageBreak())
        historia.append(Paragraph("CAPTURA DE LA PÁGINA", apartado))
        historia.append(imagen)

    historia.append(Spacer(1, 12 * mm))
    historia.append(Paragraph(
        "Informe automático. La dirección se ha abierto en un entorno aislado; "
        "en ningún momento se ha visitado desde este equipo.",
        ParagraphStyle("pie", parent=normal, fontSize=7.5,
                       textColor=colors.HexColor("#8a8f9c")),
    ))

    SimpleDocTemplate(
        str(ruta), pagesize=A4,
        leftMargin=22 * mm, rightMargin=23 * mm,
        topMargin=20 * mm, bottomMargin=18 * mm,
        title=f"QReaper — informe de {datos['url']}", author="QReaper",
    ).build(historia)


def _imagen_para_pdf(ruta_captura, Image, ImageReader, mm):
    """La captura escalada para que quepa en la página, o None si no hay.

    Que falte la captura o esté corrupta no puede impedir que salga el informe:
    ante la duda, se devuelve None y el PDF va sin imagen.
    """
    if not ruta_captura or not Path(ruta_captura).is_file():
        return None
    try:
        ancho_px, alto_px = ImageReader(str(ruta_captura)).getSize()
        if not ancho_px or not alto_px:
            return None
        ancho, alto = 165 * mm, 165 * mm * alto_px / ancho_px
        if alto > 210 * mm:  # capturas de página completa, muy alargadas
            alto = 210 * mm
            ancho = alto * ancho_px / alto_px
        return Image(str(ruta_captura), width=ancho, height=alto)
    except Exception:  # noqa: BLE001 — imagen ilegible: seguimos sin ella
        return None
