# QReaper 🔍  — Analizador Anti-Quishing

Herramienta que detecta **phishing por código QR** (*quishing*): decodifica el QR de
un correo, PDF o imagen, detona la URL oculta en un entorno seguro y emite un
**veredicto + informe**.

> El punto ciego de 2026: los filtros de correo NO leen códigos QR porque son
> imágenes. La URL maliciosa es invisible hasta que alguien la escanea.

## ¿Qué hace?

```
archivo (email/PDF/imagen)
   → [1] decode        extrae el/los QR → URL
   → [2] análisis URL  whois, typosquat, deep-links, TLD
   → [3] sandbox       abre la URL en navegador aislado → redirects + screenshot
   → [4] scoring       combina señales → nota 0-100 + veredicto
   → [5] informe       PDF / JSON / HTML
```

## Arranque rápido

> 👉 **¿Es tu primera vez en el proyecto? Ve a [`ARRANCA-AQUI.md`](ARRANCA-AQUI.md)**,
> que lo explica paso a paso y sin dar nada por sabido.

```powershell
git clone https://github.com/bdjoseluis/qreaper.git
cd qreaper
git checkout feat/TU-RAMA           # nadie trabaja en main
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
pip install -e .
pip install pytest
pytest -v                           # el smoke test en verde = entorno OK
```

Cuando los módulos estén implementados:

```powershell
qreaper analizar datasets/legitimos/ejemplo.png
```

## Módulos y responsables

| # | Módulo | Archivo | Responsable | Rama |
|---|--------|---------|-------------|------|
| 1 | Ingesta + Decode | `src/qreaper/decode.py` | Andrés (DAM) | `feat/decode-andres` |
| 2 | Análisis estático de URL | `src/qreaper/analisis_url.py` | Alex (teleco) | `feat/analisis-url-alex` |
| 3 | Sandbox de detonación | `src/qreaper/sandbox.py` | Jose | `feat/nucleo-jose` |
| 4 | Scoring | `src/qreaper/scoring.py` | Jose | `feat/nucleo-jose` |
| 5 | Informe | `src/qreaper/informe.py` | JuanFran (teleco) | `feat/informe-juanfran` |
| 6 | Interfaz (CLI/web) + Docs | `src/qreaper/cli.py` | Ismael (teleco) | `feat/interfaz-ismael` |

**Los contratos entre módulos están en [`CONTRATOS.md`](CONTRATOS.md). Léelo ANTES de picar código.**

## Reglas de equipo

- Cada uno trabaja en **su rama** (ver tabla de arriba).
- Nada se toca en `main` directo → Pull Request → Jose revisa y mergea.
- Ningún módulo depende de otro: **todos pueden arrancar a la vez**, porque las
  interfaces están cerradas en [`CONTRATOS.md`](CONTRATOS.md).
- Tu tarea está hecha cuando **su test pasa**: `pytest tests/test_contratos.py -k tu_modulo -v`

Proyecto del Máster de Ciberseguridad · Evolve Academy · 2026
