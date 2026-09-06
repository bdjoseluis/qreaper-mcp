# 🔷 Ismael — Interfaz y Documentación

> **Tu archivo:** `src/qreaper/cli.py`
> **Tu rama:** `feat/interfaz-ismael`
> **Cómo probar lo tuyo:** `qreaper --help`

---

## Qué haces tú

Tú eres **el que hace que esto se pueda usar**. Los demás hacemos motores que
devuelven diccionarios; sin ti, QReaper es un montón de código que nadie sabe
arrancar.

```
usuario ──► qreaper analizar correo.eml ──► TÚ ──► "⛔ PELIGRO (87/100) porque..."
```

Y llevas la **documentación**, que es literalmente lo que se entrega y lo que
lee el profesor. No es el módulo con más código, pero sí uno de los que más
peso tiene en la nota.

---

## Antes de nada

> 🟢 **¿No has usado GitHub nunca?** Empieza por
> **[`ISMAEL-EMPIEZA-AQUI.md`](ISMAEL-EMPIEZA-AQUI.md)**: qué es GitHub, cómo
> crearte la cuenta y cómo trabajar con botones en vez de con la consola.
> Vuelve aquí después.

Si ya lo tienes: **[`ARRANCA-AQUI.md`](../../ARRANCA-AQUI.md)** para montar el
proyecto. Vuelve aquí cuando `pytest` te funcione.

```powershell
pip install click
```

---

## Lo que ya tienes hecho

Tu archivo **ya arranca**, no partes de cero. Pruébalo ahora mismo:

```powershell
qreaper --help
qreaper analizar --help
```

Lo que hay montado es la estructura con `click`:

```python
@cli.command()
@click.argument("ruta_archivo")
@click.option("--formato", default="pdf", help="pdf | json | html")
def analizar(ruta_archivo, formato):
    resultados = pipeline.analizar_archivo(ruta_archivo, formato)
    for r in resultados:
        click.echo(r)          # ← ESTO es lo que tienes que mejorar
```

Ese `click.echo(r)` escupe el diccionario en crudo, ilegible. Tu trabajo es
convertirlo en algo que se entienda de un vistazo.

⚠️ **Tú NO analizas nada.** No metas lógica de detección en tu archivo: tú solo
pides los datos a `pipeline` y los pintas bonito. Es la regla que mantiene el
proyecto ordenado.

---

## Tus tareas

### Sprint 0 — Setup (hasta el 10 ago)
- [ ] Clonar el repo y montar el entorno
- [ ] Cambiar a tu rama y ejecutar `qreaper --help`

### Sprint 1 — Tu módulo (11–24 ago)
- [ ] **Salida por consola clara y con color** ← empieza por aquí
- [ ] Que se entienda el veredicto sin leer nada más
- [ ] Manejar errores con cariño (archivo que no existe, sin QR...)
- [ ] Escribir el README de uso: cómo se instala y cómo se ejecuta

### Sprint 2 — Integración (25 ago–1 sep)
- [ ] Web simple: subir imagen o correo → ver el resultado

### Sprint 3 — Memoria (2–5 sep)
- [x] Escribir tu parte: arquitectura y decisiones técnicas → [`ISMAEL-MEMORIA.md`](ISMAEL-MEMORIA.md)

---

## Por dónde empezar

**Paso 1 — la salida bonita.** `click` ya trae colores, no hace falta instalar
nada más:

```python
COLORES = {"PELIGRO": "red", "SOSPECHOSO": "yellow", "SEGURO": "green"}
ICONOS  = {"PELIGRO": "⛔", "SOSPECHOSO": "⚠️ ", "SEGURO": "✅"}

def pintar(resultado):
    v = resultado["scoring"]["veredicto"]
    nota = resultado["scoring"]["nota"]

    click.echo()
    click.secho(f"{ICONOS[v]}  {v}  —  {nota}/100", fg=COLORES[v], bold=True)
    click.echo(f"   Dirección: {resultado['url']}")
    if resultado["sandbox"]["url_final"] != resultado["url"]:
        click.echo(f"   Acaba en:  {resultado['sandbox']['url_final']}")
    click.echo()
    click.echo("   Por qué:")
    for motivo in resultado["scoring"]["motivos"]:
        click.echo(f"     · {motivo}")
```

Objetivo: que alguien lo vea desde lejos y **sepa si el enlace es peligroso sin
leer una sola línea**. El color y el icono hacen ese trabajo.

**Paso 2 — errores con cariño.** Si le pasan un archivo que no existe, no puede
salir un tocho rojo de Python. Que salga un mensaje normal:

```python
from pathlib import Path

if not Path(ruta_archivo).exists():
    click.secho(f"No encuentro el archivo: {ruta_archivo}", fg="red")
    raise SystemExit(1)
```

**Paso 3 — la web (Sprint 2).** Lo más rápido que puedes montar es Streamlit:
subes un archivo y muestras el resultado, en unas 20 líneas.

```powershell
pip install streamlit
```
```python
import streamlit as st
from qreaper import pipeline

archivo = st.file_uploader("Sube el correo, PDF o imagen con el QR")
if archivo:
    # guarda el archivo en disco y llama a pipeline.analizar_archivo(ruta)
    ...
```

Si Streamlit se te atraganta, con Flask también vale. Lo importante es que se
pueda enseñar el día de la demo.

---

## Un aviso sobre los tiempos

Tú dependes de que los demás terminen: hasta que Andrés, Alex y JuanFran no
tengan sus módulos, `pipeline` va a petar cuando lo llames de verdad.

**Eso no te bloquea.** Trabaja con un resultado de mentira mientras tanto:

```python
FALSO = {
    "url": "https://correos-es.top/pago",
    "sandbox": {"url_final": "https://correos-es.top/login"},
    "scoring": {"nota": 87, "veredicto": "PELIGRO",
                "motivos": ["El dominio se registró hace menos de una semana",
                            "La dirección imita a la de correos"]},
}
pintar(FALSO)
```

Así puedes dejar tu parte lista y probada antes de que ellos acaben. Cuando los
módulos estén, se conecta y ya está.

---

## Cuando termines

```powershell
git add .
git commit -m "cli: salida por consola con color y veredicto claro"
git push origin feat/interfaz-ismael
```

Entra en GitHub → **"Compare & pull request"** → lo creas y Jose lo revisa.
