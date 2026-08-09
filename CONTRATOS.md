# Contratos entre módulos

Esto es lo más importante del proyecto. Define **qué recibe y qué devuelve** cada
módulo, para que cada persona programe el suyo AISLADO y al final todo encaje.

**No cambies una firma sin avisar al grupo** (rompes el trabajo de otro).

---

## [1] decode.py  — JuanFran

```python
def decode(ruta_archivo: str) -> list[str]:
    """
    Recibe la ruta de un email (.eml), PDF o imagen.
    Extrae TODOS los códigos QR (incluidos partidos/anidados) y los decodifica.
    Devuelve la lista de URLs encontradas (sin duplicados).
    """
```
Ejemplo de salida: `["https://bit.ly/xyz", "https://correos-es.top/pago"]`

---

## [2] analisis_url.py  — Alex

```python
def analizar_url(url: str) -> dict:
    """
    Analiza una URL SIN abrirla (estático).
    Devuelve un diccionario de señales.
    """
```
Ejemplo de salida:
```python
{
    "url": "https://correos-es.top/pago",
    "edad_dominio_dias": 3,
    "tld_riesgo": "alto",
    "es_typosquat": True,
    "marca_suplantada": "correos",
    "es_acortador": False,
    "url_expandida": None,
    "deep_link": None,
}
```

---

## [3] sandbox.py  — Jose

```python
def detonar(url: str) -> dict:
    """
    Abre la URL en un navegador headless AISLADO (Docker).
    Sigue redirecciones, hace screenshot y detecta formularios de login.
    """
```
Ejemplo de salida:
```python
{
    "url_final": "https://phishing-real.xyz/login",
    "cadena_redirecciones": ["...", "..."],
    "screenshot_path": "datasets/tmp/shot_01.png",
    "hay_formulario_login": True,
    "error": None,
}
```

---

## [4] scoring.py  — Jose

```python
def puntuar(senales_url: dict, resultado_sandbox: dict) -> dict:
    """
    Combina las señales estáticas + dinámicas en una nota de riesgo.
    """
```
Ejemplo de salida:
```python
{"nota": 87, "veredicto": "PELIGRO", "motivos": ["dominio de 3 días", "typosquat de correos", "form de login"]}
```

---

## [5] informe.py  — Andrés

```python
def generar_informe(resultado: dict, formato: str = "pdf") -> str:
    """
    Recibe el resultado completo (url + señales + sandbox + scoring)
    y genera el informe. Devuelve la ruta del archivo generado.
    formato: "pdf" | "json" | "html"
    """
```

---

## [6] cli.py  — 5ª persona

Orquesta la llamada a todo lo anterior a través de `pipeline.analizar_archivo()`.
No implementa lógica de análisis, solo la interfaz de usuario.
