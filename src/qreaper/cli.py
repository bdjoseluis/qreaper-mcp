"""
Módulo 6 — Interfaz (CLI)  ·  Responsable: Ismael

Objetivo: interfaz de usuario. NO implementa lógica de análisis.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.rule import Rule

from . import pipeline


console = Console()

VERDICT_STYLES = {
    "SEGURO": "green",
    "SOSPECHOSO": "yellow",
    "PELIGRO": "red",
}

VERDICT_LABELS = {
    "SEGURO": "Seguro",
    "SOSPECHOSO": "Sospechoso",
    "PELIGRO": "Peligro",
}

MAX_URL_DISPLAY = 60


def truncate_url(url: str, max_len: int = MAX_URL_DISPLAY) -> str:
    """Truncate URL at midpoint with ellipsis."""
    if len(url) <= max_len:
        return url
    half = (max_len - 1) // 2
    return f"{url[:half]}…{url[-(max_len - half - 1):]}"


def format_verdict(verdict: str, no_color: bool = False) -> Text:
    """Format verdict with color and label."""
    style = VERDICT_STYLES.get(verdict, "white")
    label = VERDICT_LABELS.get(verdict, verdict)
    text = Text(label)
    if not no_color:
        text.stylize(style)
    return text


def format_score(score: int, no_color: bool = False) -> Text:
    """Format risk score with color based on threshold."""
    if score >= 70:
        color = "red"
    elif score >= 40:
        color = "yellow"
    else:
        color = "green"
    text = Text(f"{score}/100")
    if not no_color:
        text.stylize(color)
    return text


def render_result(result: dict[str, Any], no_color: bool = False, verbose: bool = False) -> None:
    """Render a single analysis result."""
    url = result.get("url", "")
    senales = result.get("senales", {})
    sandbox = result.get("sandbox", {})
    scoring = result.get("scoring", {})
    informe = result.get("informe", "")

    verdict = scoring.get("verdict", "DESCONOCIDO")
    score = scoring.get("nota", 0)
    reasons = scoring.get("motivos", [])

    # Header panel with URL and verdict
    header_text = Text()
    header_text.append("Archivo: ", style="dim")
    header_text.append(truncate_url(url))
    header_text.append("  ")
    header_text.append(str(format_verdict(verdict, no_color)))
    header_text.append("  ")
    header_text.append(str(format_score(score, no_color)))

    console.print(Panel(header_text, expand=False, border_style="dim" if no_color else None))

    # Static signals table
    if senales:
        table = Table(show_header=False, box=None, padding=(0, 1, 0, 0))
        table.add_column("Clave", style="dim" if not no_color else None)
        table.add_column("Valor")

        if "edad_dominio_dias" in senales:
            age = senales["edad_dominio_dias"]
            age_style = "red" if age < 30 else "yellow" if age < 365 else "green"
            age_text = Text(f"{age} días")
            if not no_color:
                age_text.stylize(age_style)
            table.add_row("Edad del dominio", age_text)

        if "tld_riesgo" in senales:
            tld = senales["tld_riesgo"]
            tld_style = {"alto": "red", "medio": "yellow", "bajo": "green"}.get(tld, "white")
            tld_text = Text(tld.capitalize())
            if not no_color:
                tld_text.stylize(tld_style)
            table.add_row("Riesgo TLD", tld_text)

        if "es_typosquat" in senales and senales["es_typosquat"]:
            brand = senales.get("marca_suplantada", "desconocida")
            typosquat_text = Text(f"Sí ({brand})")
            if not no_color:
                typosquat_text.stylize("red")
            table.add_row("Typosquatting", typosquat_text)

        if "es_acortador" in senales and senales["es_acortador"]:
            expanded = senales.get("url_expandida")
            if expanded:
                table.add_row("Acortador", Text(f"Sí → {truncate_url(expanded)}", style="yellow" if not no_color else None))
            else:
                table.add_row("Acortador", Text("Sí", style="yellow" if not no_color else None))

        if "deep_link" in senales and senales["deep_link"]:
            table.add_row("Deep link", Text(senales["deep_link"], style="yellow" if not no_color else None))

        console.print(Rule("Análisis estático", style="dim" if no_color else None))
        console.print(table)

    # Dynamic analysis (sandbox)
    if sandbox and verbose:
        table = Table(show_header=False, box=None, padding=(0, 1, 0, 0))
        table.add_column("Clave", style="dim" if not no_color else None)
        table.add_column("Valor")

        if sandbox.get("url_final"):
            table.add_row("URL final", Text(truncate_url(sandbox["url_final"])))

        if sandbox.get("cadena_redirecciones"):
            chain = sandbox["cadena_redirecciones"]
            if chain:
                table.add_row("Redirecciones", Text(str(len(chain)) + " saltos"))
                if verbose:
                    for i, hop in enumerate(chain, 1):
                        table.add_row(f"  {i}.", Text(truncate_url(hop), style="dim"))

        if sandbox.get("screenshot_path"):
            table.add_row("Captura", Text(sandbox["screenshot_path"], style="dim"))

        if sandbox.get("hay_formulario_login"):
            brand = sandbox.get("login_form_brand", "desconocida")
            login_text = Text(f"Detectado ({brand})")
            if not no_color:
                login_text.stylize("red")
            table.add_row("Formulario login", login_text)

        console.print(Rule("Análisis dinámico", style="dim" if no_color else None))
        console.print(table)

    # Scoring reasons
    if reasons:
        console.print(Rule("Motivos del veredicto", style="dim" if no_color else None))
        for i, reason in enumerate(reasons, 1):
            reason_text = Text(f"{i}. {reason}")
            if not no_color:
                reason_text.stylize("dim")
            console.print(reason_text)

    # Report path
    if informe:
        report_text = Text()
        report_text.append("Informe: ", style="dim")
        report_text.append(informe)
        console.print(report_text)

    console.print()  # spacing between results


def render_json_output(results: list[dict[str, Any]]) -> None:
    """Render results as JSON."""
    click.echo(json.dumps(results, indent=2, ensure_ascii=False))


@click.group()
@click.option("--no-color", is_flag=True, help="Desactivar colores en la salida")
@click.pass_context
def cli(ctx: click.Context, no_color: bool):
    """QReaper - Analizador Anti-Quishing."""
    ctx.ensure_object(dict)
    ctx.obj["no_color"] = no_color
    ctx.obj["console"] = Console(no_color=no_color, force_terminal=not no_color)


@cli.command()
@click.argument("ruta_archivo", type=click.Path(exists=True, path_type=Path))
@click.option("--formato", default="pdf", type=click.Choice(["pdf", "json", "html"]), help="Formato del informe")
@click.option("--json", "as_json", is_flag=True, help="Salida en JSON")
@click.option("--verbose", "-v", is_flag=True, help="Mostrar detalles del análisis dinámico")
@click.pass_context
def analizar(ctx: click.Context, ruta_archivo: Path, formato: str, as_json: bool, verbose: bool):
    """Analiza un archivo (email/PDF/imagen) en busca de quishing."""
no_color = ctx.obj.get("no_color", False)

    try:
        resultados = pipeline.analizar_archivo(str(ruta_archivo), formato)
    except NotImplementedError as e:
        console = ctx.obj["console"]
        console.print(f"[red]Error:[/red] Módulo no implementado: {e}")
        sys.exit(1)
    except Exception as e:
        console = ctx.obj["console"]
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if as_json:
        render_json_output(resultados)
        return

    console = ctx.obj["console"]

    if not resultados:
        console.print("[yellow]No se encontraron códigos QR en el archivo.[/yellow]")
        return

    # Header
    console.print(Rule(f"QReaper — Análisis de {ruta_archivo.name}", style="dim" if no_color else None))
    console.print()

    for result in resultados:
        render_result(result, no_color=no_color, verbose=verbose)

    # Summary
    total = len(resultados)
    peligrosos = sum(1 for r in resultados if r.get("scoring", {}).get("verdict") == "PELIGRO")
    sospechosos = sum(1 for r in resultados if r.get("scoring", {}).get("verdict") == "SOSPECHOSO")
    seguros = sum(1 for r in resultados if r.get("scoring", {}).get("verdict") == "SEGURO")

    summary = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    summary.add_column("Métrica", style="dim" if not no_color else None)
    summary.add_column("Valor")

    summary.add_row("Total analizados", Text(str(total), style="bold"))
    if peligrosos:
        p_text = Text(str(peligrosos))
        if not no_color:
            p_text.stylize("red")
        summary.add_row("Peligro", p_text)
    if sospechosos:
        s_text = Text(str(sospechosos))
        if not no_color:
            s_text.stylize("yellow")
        summary.add_row("Sospechoso", s_text)
    if seguros:
        s_text = Text(str(seguros))
        if not no_color:
            s_text.stylize("green")
        summary.add_row("Seguro", s_text)

    console.print(Rule("Resumen", style="dim" if no_color else None))
    console.print(summary)


if __name__ == "__main__":
    cli()