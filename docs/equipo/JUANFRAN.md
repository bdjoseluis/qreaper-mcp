# 🔷 JuanFran — Informe y Dataset

> **Tu archivo:** `src/qreaper/informe.py`
> **Tu rama:** `feat/informe-juanfran`
> **Tu test:** `pytest tests/test_contratos.py -k informe -v`

---

## Qué haces tú

Tú eres **la cara visible del proyecto**. Todo el análisis que hacen los demás
acaba en un diccionario lleno de datos, y tú lo conviertes en un informe que una
persona normal pueda leer y entender.

```
{url, señales, capturas, nota: 87, veredicto: PELIGRO}  ──►  TÚ  ──►  informe.pdf
```

Ojo con esto: **el informe es lo que se enseña el día de la presentación.** Los
demás módulos se ven en la consola; el tuyo se ve en pantalla. Si queda bien,
el proyecto entero parece bueno.

Además llevas el **dataset**: los QR de ejemplo con los que probamos que la
herramienta acierta.

---

## Antes de nada

Si todavía no has montado el proyecto: **[`ARRANCA-AQUI.md`](../../ARRANCA-AQUI.md)**.
Vuelve aquí cuando `pytest` te funcione.

```powershell
pip install reportlab jinja2
```

---

## Tu contrato (esto NO se toca sin avisar)

```python
def generar_informe(resultado: dict, formato: str = "pdf") -> str:
    ...
```

- **Recibe:** el resultado completo del análisis + el formato que quieren.
- **Devuelve:** la **ruta del archivo** que has creado, como texto.
- El archivo **tiene que existir** de verdad y su extensión **tiene que
  coincidir** con el formato pedido (`"pdf"` → `informe.pdf`).
- Tienes que soportar los tres: `"pdf"`, `"json"` y `"html"`.

---

## Lo que te llega (esto es oro, léelo bien)

```python
resultado = {
    "url": "https://correos-es.top/pago",
    "senales": {          # ← de Alex
        "edad_dominio_dias": 3,
        "tld_riesgo": "alto",
        "es_typosquat": True,
        "marca_suplantada": "correos",
    },
    "sandbox": {          # ← de Jose
        "url_final": "https://correos-es.top/login",
        "cadena_redirecciones": ["...", "..."],
        "screenshot_path": "datasets/tmp/shot_01.png",   # ¡una foto de la web!
        "hay_formulario_login": True,
    },
    "scoring": {          # ← de Jose
        "nota": 87,
        "veredicto": "PELIGRO",
        "motivos": ["El dominio se registró hace menos de una semana",
                    "La dirección imita a la de correos",
                    "La página pide usuario y contraseña"],
        "detalle": [{"senal": "typosquat", "puntos": 25, "motivo": "..."}],
    },
}
```

Dos regalos que ya tienes hechos:

1. **`motivos`** ya viene en lenguaje llano. No tienes que traducir nada
   técnico: se pinta tal cual y se entiende.
2. **`detalle`** trae los puntos de cada señal → con eso puedes hacer una
   **tabla o una barra de "de dónde sale la nota"**, que queda muy bien.

Y hay una función hecha para la frase final:

```python
from qreaper.scoring import recomendacion
recomendacion("PELIGRO")   # "NO introduzcas ningún dato. Borra el mensaje y repórtalo."
```

---

## Tus tareas

### Sprint 0 — Setup (hasta el 10 ago)
- [ ] Clonar el repo y montar el entorno
- [ ] Cambiar a tu rama y ejecutar tu test (tiene que fallar diciendo tu nombre)

### Sprint 1 — Tu módulo (11–24 ago)
- [ ] **Formato JSON** ← empieza por aquí, son 4 líneas y ya tienes 1 test verde
- [ ] Formato HTML con jinja2
- [ ] Formato PDF con reportlab
- [ ] Meter en el informe: URL, señales, captura, nota, motivos y recomendación
- [ ] Dataset: 30 QR legítimos
- [ ] Dataset: 30 QR maliciosos (simulados, ver abajo)

### Sprint 2 — Integración (25 ago–1 sep)
- [ ] El informe de ejemplo bueno para la demo

### Sprint 3 — Memoria (2–5 sep)
- [ ] Escribir tu parte: resultados y métricas del dataset

---

## Por dónde empezar (el orden importa)

**Paso 1 — JSON. Con esto ya tienes un test en verde hoy mismo:**

```python
import json
from pathlib import Path

def generar_informe(resultado: dict, formato: str = "pdf") -> str:
    if formato == "json":
        ruta = Path("informe.json")
        ruta.write_text(json.dumps(resultado, indent=2, ensure_ascii=False),
                        encoding="utf-8")
        return str(ruta)
    raise NotImplementedError(f"formato {formato} todavía no")
```

**Paso 2 — HTML.** Es el que mejor se ve y el más fácil de los "bonitos".
Puedes usar una plantilla de texto normal con jinja2:

```python
from jinja2 import Template

PLANTILLA = Template("""
<html><body style="font-family: sans-serif">
  <h1 style="color: {{ color }}">{{ r.scoring.veredicto }} — {{ r.scoring.nota }}/100</h1>
  <p><b>Dirección analizada:</b> {{ r.url }}</p>
  <h2>Por qué</h2>
  <ul>{% for m in r.scoring.motivos %}<li>{{ m }}</li>{% endfor %}</ul>
  {% if r.sandbox.screenshot_path %}
    <h2>Así se ve la página</h2>
    <img src="{{ r.sandbox.screenshot_path }}" width="600">
  {% endif %}
</body></html>
""")
```

Truco para que quede profesional: **color según el veredicto** — rojo para
PELIGRO, naranja para SOSPECHOSO, verde para SEGURO.

**Paso 3 — PDF con reportlab.** Es el más pesado, déjalo para el final:

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

c = canvas.Canvas("informe.pdf", pagesize=A4)
c.setFont("Helvetica-Bold", 20)
c.drawString(50, 780, "QReaper — Informe de análisis")
c.drawImage(resultado["sandbox"]["screenshot_path"], 50, 400, width=400, height=250)
c.save()
```

---

## El dataset (tu otra tarea)

Van en `datasets/legitimos/` y `datasets/maliciosos/`. Ya tienes un ejemplo de
cada uno para que veas el formato.

Para generar QR fácil:
```powershell
pip install qrcode
```
```python
import qrcode
qrcode.make("https://correos-es.top/pago-pendiente").save("datasets/maliciosos/01.png")
```

⚠️ **Los "maliciosos" son SIMULADOS.** Te inventas direcciones con pinta de
fraude (`correos-es.top`, `dgt-multas.xyz`, `bbva-seguridad.click`), pero **no
metas enlaces de phishing reales** en el repo. Ni falta que hace: lo que
probamos es que el detector puntúa alto, y con dominios inventados con las
mismas características vale igual.

---

## Cuando termines

```powershell
pytest tests/test_contratos.py -k informe -v     # tiene que salir PASSED
git add .
git commit -m "informe: genero JSON y HTML"
git push origin feat/informe-juanfran
```

Entra en GitHub → **"Compare & pull request"** → lo creas y Jose lo revisa.

Puedes ir subiendo a trozos: en cuanto tengas el JSON, súbelo. No esperes a
tenerlo todo.
