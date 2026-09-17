# QReaper — API REST y servidor MCP

Capa de acceso al motor anti-quishing (responsable: Jose). Misma lógica que el
CLI, expuesta por HTTP y como herramientas MCP. Cubre los requisitos 3
("API o webhook de verdad, ideal empaquetada como MCP tool") de la práctica.

## Instalación

```bash
pip install -e ".[api,mcp]"     # o  ".[todo]"  para todo el paquete
```

## API REST (FastAPI)

Arranque en local:

```bash
qreaper-api                     # escucha en 0.0.0.0:8000
# equivalente:
uvicorn qreaper.api:app --reload
```

Documentación interactiva (Swagger) auto-generada: <http://localhost:8000/docs>

### Endpoints

| Método | Ruta                     | Qué hace |
|--------|--------------------------|----------|
| GET    | `/`                      | Metadatos y lista de endpoints |
| GET    | `/salud`                 | Healthcheck (`{"estado":"ok"}`) |
| POST   | `/analizar/url`          | Analiza una URL. Cuerpo: `{"url": "...", "formato": null\|"pdf"\|"html"\|"json"}` |
| POST   | `/analizar/archivo`      | Sube imagen/PDF/`.eml` (multipart, campo `archivo`), extrae los QR y analiza cada URL |
| GET    | `/historial`             | Lista los análisis guardados en la BD. Query: `limite`, `veredicto` |
| GET    | `/historial/{id}`        | Un análisis concreto por id |

Ejemplos:

```bash
# Analizar una URL
curl -X POST http://localhost:8000/analizar/url \
  -H "Content-Type: application/json" \
  -d '{"url":"https://correos-es.top/pago"}'

# Analizar un archivo con QR
curl -X POST "http://localhost:8000/analizar/archivo" \
  -F "archivo=@email_sospechoso.eml"

# Consultar el historial (solo PELIGRO)
curl "http://localhost:8000/historial?veredicto=PELIGRO&limite=10"
```

## Servidor MCP

Expone el motor como herramientas invocables desde Claude (Desktop o Code).
Transporte stdio.

```bash
qreaper-mcp                     # o  python -m qreaper.mcp_server
```

Registro en Claude Code:

```bash
claude mcp add qreaper -- qreaper-mcp
```

### Herramientas publicadas

- `analizar_url(url)` — veredicto de riesgo de una URL.
- `analizar_archivo(ruta)` — analiza un fichero local (imagen/PDF/`.eml`).
- `historial(limite, veredicto)` — consulta los análisis guardados.

Devuelven un resumen compacto (`veredicto`, `nota`, `motivos`, `url_final`)
para no malgastar tokens del asistente.

## Pruebas

```bash
pytest tests/test_api.py -q     # 11 pruebas, pipeline y BD simulados (sin red ni Docker)
```
