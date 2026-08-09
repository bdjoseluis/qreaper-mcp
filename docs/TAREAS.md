# Reparto de tareas

## Sprints
- **Sprint 0 (esta semana):** repo + contratos + cada uno el "hola mundo" de su módulo.
- **Sprint 1:** cada módulo funcional por separado.
- **Sprint 2:** integración + dataset + informe.
- **Sprint 3:** pulido + demo + memoria.

## Por persona

### Jose — Lead + Núcleo (sandbox.py, scoring.py, pipeline.py)
- [ ] Repo, estructura y contratos ✅
- [ ] Sandbox Playwright en Docker
- [ ] Redirects + screenshot + detección de login
- [ ] Motor de scoring
- [ ] Revisar PRs e integrar

### JuanFran — Ingesta + Decode (decode.py)
- [ ] Parsear .eml y extraer imágenes
- [ ] Extraer imágenes de PDF
- [ ] Decodificar QR (pyzbar/OpenCV)
- [ ] Manejar imágenes de baja calidad
- [ ] Soportar QR partidos/anidados

### Alex — Análisis estático de URL (analisis_url.py)
- [ ] whois / edad de dominio
- [ ] TLD de riesgo
- [ ] typosquat / homoglifos vs marcas
- [ ] expandir acortadores
- [ ] detectar deep-links

### Andrés — Informe (informe.py)
- [ ] Plantilla PDF/JSON/HTML
- [ ] Volcar url + señales + screenshot + nota
- [ ] Informe de ejemplo para la demo

### 5ª persona — Interfaz + Dataset (cli.py, datasets/)
- [ ] CLI usable
- [ ] Web simple (subir → veredicto)
- [ ] Dataset de QR maliciosos y legítimos
- [ ] Documentación de uso
