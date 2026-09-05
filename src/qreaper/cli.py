"""
Módulo 6 — Interfaz (CLI)  ·  Responsable: Ismael (implementado por Jose)

Interfaz de línea de comandos. No implementa lógica de análisis: llama al
pipeline y presenta el resultado de forma legible.

Uso:
    qreaper analizar imagen.png
    qreaper analizar email.eml --formato html
    qreaper url https://correos-es.top/pago
"""
from __future__ import annotations

import json
import logging
import sys

import click

from . import pipeline

log = logging.getLogger("qreaper")


# ---------------------------------------------------------------------------
# Presentación
# ---------------------------------------------------------------------------

COLOR_VEREDICTO = {
    "PELIGRO": "red",
    "SOSPECHOSO": "yellow",
    "SEGURO": "green",
    "DESCONOCIDO": "white",
}


def _pinta_veredicto(resultado: dict) -> None:
    """Imprime el bloque cabecera de un resultado en la consola."""
    url = resultado.get("url", "?")
    scoring = resultado.get("scoring") or {}
    veredicto = scoring.get("veredicto", "DESCONOCIDO")
    nota = scoring.get("nota")
    color = COLOR_VEREDICTO.get(veredicto, "white")

    click.echo("─" * 68)
    click.echo(click.style(f"  {veredicto}", fg=color, bold=True), nl=False)
    if nota is not None:
        click.echo(f"   nota {nota}/100", nl=False)
    click.echo(f"   {url}")
    click.echo("─" * 68)

    motivos = scoring.get("motivos") or []
    if motivos:
        click.echo("Motivos:")
        for m in motivos:
            click.echo(f"  • {m}")

    sandbox = resultado.get("sandbox") or {}
    if sandbox.get("url_final") and sandbox["url_final"] != url:
        click.echo(f"URL final tras redirecciones: {sandbox['url_final']}")
    if sandbox.get("screenshot_path"):
        click.echo(f"Captura: {sandbox['screenshot_path']}")

    ruta_informe = resultado.get("informe")
    if ruta_informe:
        click.echo(click.style(f"Informe: {ruta_informe}", fg="cyan"))

    errores = resultado.get("errores") or {}
    if errores:
        click.echo(click.style("Avisos (módulos que no dieron datos):", fg="yellow"))
        for modulo, motivo in errores.items():
            click.echo(f"  ! {modulo}: {motivo}")


def _configurar_log(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option("0.1.0", prog_name="qreaper")
@click.option("--verbose", "-v", is_flag=True, help="Logs detallados en stderr.")
@click.pass_context
def cli(ctx, verbose):
    """QReaper — analizador anti-quishing.

    Detecta URLs escondidas en códigos QR (email, PDF, imagen), las abre en un
    sandbox aislado y genera un informe de riesgo.
    """
    ctx.ensure_object(dict)
    _configurar_log(verbose)


@cli.command()
@click.argument("ruta_archivo", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--formato",
    type=click.Choice(["pdf", "html", "json"], case_sensitive=False),
    default="html",
    show_default=True,
    help="Formato del informe generado.",
)
@click.option(
    "--json-out",
    is_flag=True,
    help="Imprime el resultado crudo en JSON por stdout (útil para pipes).",
)
def analizar(ruta_archivo, formato, json_out):
    """Analiza un archivo (email .eml, PDF o imagen) buscando quishing."""
    resultados = pipeline.analizar_archivo(ruta_archivo, formato.lower())

    if json_out:
        click.echo(json.dumps(resultados, indent=2, ensure_ascii=False, default=str))
        return

    if not resultados:
        click.echo(click.style("No se han encontrado códigos QR con URL.", fg="yellow"))
        return

    for i, r in enumerate(resultados, 1):
        if len(resultados) > 1:
            click.echo(click.style(f"\n[QR {i}/{len(resultados)}]", bold=True))
        _pinta_veredicto(r)

    _pinta_resumen(resultados)


@cli.command()
@click.argument("url")
@click.option(
    "--formato",
    type=click.Choice(["pdf", "html", "json", "ninguno"], case_sensitive=False),
    default="html",
    show_default=True,
    help="Formato del informe generado. 'ninguno' no genera archivo.",
)
@click.option("--json-out", is_flag=True, help="Salida cruda en JSON.")
def url(url, formato, json_out):
    """Analiza UNA URL directa (útil para probar sin fabricar un QR)."""
    formato_arg = None if formato.lower() == "ninguno" else formato.lower()
    resultado = pipeline.analizar_url_suelta(url, formato_arg)

    if json_out:
        click.echo(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
        return

    _pinta_veredicto(resultado)


def _pinta_resumen(resultados: list[dict]) -> None:
    """Al final: cuántos han caído en cada bucket."""
    total = len(resultados)
    peligro = sum(1 for r in resultados if (r.get("scoring") or {}).get("veredicto") == "PELIGRO")
    sospe = sum(1 for r in resultados if (r.get("scoring") or {}).get("veredicto") == "SOSPECHOSO")
    seguro = sum(1 for r in resultados if (r.get("scoring") or {}).get("veredicto") == "SEGURO")
    click.echo("─" * 68)
    click.echo(
        f"Resumen: {total} URL(s) — "
        + click.style(f"{peligro} peligro", fg="red")
        + " · "
        + click.style(f"{sospe} sospechoso", fg="yellow")
        + " · "
        + click.style(f"{seguro} seguro", fg="green")
    )


def main():
    try:
        cli(obj={})
    except click.ClickException:
        raise
    except Exception as e:  # noqa: BLE001
        log.exception("Fallo inesperado")
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
