"""
Demo end-to-end del pipeline QReaper sobre los 3 fixtures de campaña real
+ el ejemplo legítimo. Mockea el sandbox para no depender de la red.

Genera los informes HTML dentro de demo/informes/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"
sys.path.insert(0, str(SRC))

os.chdir(Path(__file__).resolve().parent / "informes")

from qreaper import pipeline, sandbox  # noqa: E402


def sandbox_mock(url, **kwargs):
    """Simula lo que devolvería el sandbox sin abrir la URL."""
    hostname = url.split("//", 1)[-1].split("/", 1)[0]
    return {
        "url_final": url,
        "cadena_redirecciones": [url],
        "screenshot_path": None,
        "hay_formulario_login": "login" in url.lower() or "verif" in url.lower(),
        "error": None,
        "aislamiento": "mock-para-demo",
    }


CASOS = [
    ("BBVA (email .eml)", RAIZ / "tests/fixtures/campanas_reales/bbva-verificar-cuenta.eml"),
    ("Correos (email .eml)", RAIZ / "tests/fixtures/campanas_reales/correos-paquete-retenido.eml"),
    ("DGT (PDF)", RAIZ / "tests/fixtures/campanas_reales/dgt-multa-pendiente.pdf"),
    ("Ejemplo legítimo b-dev.es (PNG)", RAIZ / "datasets/legitimos/ejemplo.png"),
]


def main():
    print("=" * 72)
    print(" QReaper — demo end-to-end (sandbox mockeado)")
    print("=" * 72)

    with patch.object(sandbox, "detonar", sandbox_mock):
        for etiqueta, ruta in CASOS:
            print(f"\n▶ {etiqueta}: {ruta.name}")
            print("-" * 72)
            resultados = pipeline.analizar_archivo(str(ruta), formato_informe="html")
            if not resultados:
                print("  (no se encontraron QR con URL)")
                continue
            for r in resultados:
                sc = r["scoring"]
                print(f"  URL     : {r['url']}")
                print(f"  Veredicto: {sc['veredicto']}  nota {sc['nota']}/100")
                print(f"  Motivos :")
                for m in sc["motivos"][:5]:
                    print(f"    - {m}")
                print(f"  Informe : {r['informe']}")

    print("\n" + "=" * 72)
    print(" Informes guardados en:", (Path.cwd()).resolve())


if __name__ == "__main__":
    main()
