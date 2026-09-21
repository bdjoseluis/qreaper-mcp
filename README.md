# QReaper 🔍 — Anti-Quishing MCP Tool

**Install as MCP — paste this URL:**

```
https://github.com/bdjoseluis/qreaper-mcp
```

---

## What is QReaper?

QReaper detects **QR-code phishing (quishing)**: it extracts URLs hidden in QR codes (from emails, PDFs or images), opens them in an isolated Chromium sandbox, and returns a risk verdict.

> QR codes are images — email filters can't read them. The malicious URL is invisible until someone scans it. QReaper fixes that.

## Install as MCP

```bash
pip install "qreaper[todo] @ git+https://github.com/bdjoseluis/qreaper-mcp.git"
playwright install chromium
claude mcp add qreaper -- qreaper-mcp
```

> Si `qreaper-mcp` no está en el PATH tras instalar, arráncalo con
> `python -m qreaper.mcp_server` (mismo servidor).

Once installed, your AI assistant can use it directly:

> *"Analyze this URL: https://correos-es.pago-pendiente.top/multa"*  
> *"Scan this image for malicious QR codes"*  
> *"Show me the last phishing detections"*

### Available tools

| Tool | What it does |
|------|-------------|
| `analizar_url(url)` | Analyze a URL → DANGER / SUSPICIOUS / SAFE + score + reasons |
| `analizar_archivo(ruta)` | Scan a local file (image/PDF/.eml) for QR codes |
| `historial(limite, veredicto)` | Query stored analysis history |

## Live demo

- Web UI: **https://qreaper.b-dev.es/app**
- API docs: **https://qreaper.b-dev.es/docs**

## Analysis pipeline

```
file (email / PDF / image)
   → decode        extract QR → URL
   → url analysis  whois · typosquatting · risky TLD · deep-links
   → sandbox       isolated Chromium → redirects + screenshot
   → scoring       0–100 score · DANGER / SUSPICIOUS / SAFE
   → report        PDF / HTML / JSON
```

## CLI & API

```bash
# CLI
qreaper analizar email.eml
qreaper url https://correos-es.top/pago --formato pdf

# API server
qreaper-api   # → http://localhost:8000/docs
```

## Docker

```bash
docker compose -f deploy/docker-compose.vps.yml up -d --build
```

---

Built at Evolve Academy · Cybersecurity Master 2026
