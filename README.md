# QReaper 🔍 — Anti-Quishing Analyzer

Detects **QR-code phishing (quishing)**: decodes QR codes from emails, PDFs or images, detonates the hidden URL in an isolated sandbox and returns a **risk verdict + report**.

> The blind spot of 2026: email filters can't read QR codes because they're images. The malicious URL is invisible until someone scans it. QReaper fixes that.

## What it does

```
file (email / PDF / image / raw QR)
   → [1] decode       extract QR → URL
   → [2] url analysis whois, typosquat detection, deep-links, risky TLD
   → [3] sandbox      open URL in isolated Chromium → follows redirects + screenshot
   → [4] scoring      combine signals → score 0-100 + DANGER / SUSPICIOUS / SAFE
   → [5] report       PDF / JSON / HTML
```

## Install

```bash
git clone https://github.com/bdjoseluis/qreaper.git
cd qreaper
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\Activate.ps1    # Windows
pip install -e ".[todo]"
playwright install chromium
```

## Use as a CLI

```bash
qreaper analizar path/to/image.png
qreaper analizar path/to/email.eml --formato pdf
```

## Use as an API

```bash
qreaper-api          # starts FastAPI on http://localhost:8000
# interactive docs → http://localhost:8000/docs
# web UI           → http://localhost:8000/app
```

## Use as an MCP tool (Claude Code / Claude Desktop)

Register the server once:

```bash
claude mcp add qreaper -- qreaper-mcp
```

Then just talk to Claude:

> *"Analyze this suspicious URL: https://correos-es.pago-pendiente.top/pago"*  
> *"Scan this attached image for malicious QR codes"*  
> *"Show me the last 10 phishing detections"*

Claude will call `analizar_url`, `analizar_archivo` or `historial` automatically.

### Available MCP tools

| Tool | Description |
|------|-------------|
| `analizar_url(url)` | Analyze a URL → verdict + score + reasons |
| `analizar_archivo(ruta)` | Scan a local file for QR codes and analyze each URL |
| `historial(limite, veredicto)` | Query stored analysis history |

## Live demo

Public instance: **https://qreaper.b-dev.es**  
Web UI: **https://qreaper.b-dev.es/app**  
API docs: **https://qreaper.b-dev.es/docs**

## Deploy with Docker

```bash
cd deploy
docker compose -f docker-compose.vps.yml up -d --build
```

Traefik-ready. Chromium sandbox included.

## Environment variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `QREAPER_SANDBOX` | `local` / `off` | `local` | `off` disables Chromium detonation |
| `QREAPER_EN_CONTENEDOR` | `1` | — | Set inside Docker: enables `--no-sandbox` for Chromium |

## Project structure

```
src/qreaper/
├── decode.py        # QR extraction (pyzbar / PyMuPDF / eml)
├── analisis_url.py  # static URL signals
├── sandbox.py       # Playwright Chromium detonation
├── scoring.py       # risk scoring engine
├── informe.py       # PDF / HTML / JSON reports
├── pipeline.py      # orchestrator
├── api.py           # FastAPI REST layer
├── mcp_server.py    # MCP server (stdio)
└── cli.py           # Click CLI
```

---

Built at Evolve Academy · Cybersecurity Master 2026
