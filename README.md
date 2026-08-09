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

```bash
git clone <repo>
cd qreaper
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m qreaper.cli analizar datasets/legitimos/ejemplo.png
```

## Módulos y responsables

| # | Módulo | Archivo | Responsable |
|---|--------|---------|-------------|
| 1 | Ingesta + Decode | `src/qreaper/decode.py` | Andrés (DAM) |
| 2 | Análisis estático de URL | `src/qreaper/analisis_url.py` | Alex (teleco) |
| 3 | Sandbox de detonación | `src/qreaper/sandbox.py` | Jose |
| 4 | Scoring | `src/qreaper/scoring.py` | Jose |
| 5 | Informe | `src/qreaper/informe.py` | JuanFran |
| 6 | Interfaz (CLI/web) + Dataset | `src/qreaper/cli.py` | Ismael (teleco) |

**Los contratos entre módulos están en [`CONTRATOS.md`](CONTRATOS.md). Léelo ANTES de picar código.**

## Reglas de equipo

- Cada uno trabaja en **su rama** (`feat/decode`, `feat/analisis-url`, ...).
- Nada se toca en `main` directo → Pull Request → Jose revisa y mergea.
- Módulos **2 y 3 arrancan ya** (no dependen de nadie).

Proyecto del Máster de Ciberseguridad · Evolve Academy · 2026
