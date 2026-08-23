# 🔷 Alex — Análisis de la URL (sin abrirla)

> **Tu archivo:** `src/qreaper/analisis_url.py`
> **Tu rama:** `feat/analisis-url-alex`
> **Tu test:** `pytest tests/test_contratos.py -k analisis -v`

---

## Qué haces tú

Te llega una dirección web sospechosa y tienes que **buscarle las pegas sin
abrirla**. Eres el que la mira desde fuera: quién la registró, cuándo, si imita
a una marca conocida, si esconde el destino real...

```
"https://correos-es.top/pago"  ──►  TÚ  ──►  {dominio de 3 días, TLD peligroso,
                                               imita a Correos, ...}
```

Es la parte más de **redes y dominios** del proyecto, por eso te toca a ti. Y es
la que más "chicha" da para la memoria: aquí es donde se explica *por qué* una
dirección da mala espina.

---

## Antes de nada

Si todavía no has montado el proyecto: **[`ARRANCA-AQUI.md`](../../ARRANCA-AQUI.md)**.
Vuelve aquí cuando `pytest` te funcione.

```powershell
pip install python-whois tldextract requests
```

---

## Tu contrato (esto NO se toca sin avisar)

```python
def analizar_url(url: str) -> dict:
    ...
```

Devuelves **siempre** un diccionario con **estas 8 claves**, aunque alguna vaya
vacía. Si te falta una, rompes el módulo de Jose:

```python
{
    "url": "https://correos-es.top/pago",   # la que te han pasado, tal cual
    "edad_dominio_dias": 3,                 # int, o None si no se sabe
    "tld_riesgo": "alto",                   # "alto" | "medio" | "bajo"
    "es_typosquat": True,                   # True / False
    "marca_suplantada": "correos",          # texto, o None
    "es_acortador": False,                  # True / False
    "url_expandida": None,                  # el destino real, o None
    "deep_link": None,                      # "telegram://..." o None
}
```

⚠️ **Regla de oro: tú NO abres la página.** Eso lo hace Jose en el sandbox, que
está aislado. La única excepción es seguir un acortador (y ahí solo se pide la
cabecera, no el contenido — te lo explico abajo).

---

## Tus tareas

### Sprint 0 — Setup (hasta el 10 ago)
- [ ] Clonar el repo y montar el entorno
- [ ] Cambiar a tu rama y ejecutar tu test (tiene que fallar diciendo tu nombre)

### Sprint 1 — Tu módulo (11–24 ago)
- [ ] **Devolver el diccionario con las 8 claves** (aunque sea con valores fijos) ← empieza por aquí
- [ ] Edad del dominio con `whois`
- [ ] Clasificar el TLD por riesgo
- [ ] Detectar typosquatting / homoglifos contra una lista de marcas
- [ ] Expandir acortadores (`bit.ly` → destino real)
- [ ] Detectar deep-links (`telegram://`, `intent://`)

### Sprint 2 — Integración (25 ago–1 sep)
- [ ] Afinar con los falsos negativos que salgan del dataset

### Sprint 3 — Memoria (2–5 sep)
- [ ] Escribir tu parte: análisis de dominios y tipos de amenaza

---

## Por dónde empezar (el orden importa)

**Paso 1 — el esqueleto que ya pasa media prueba.** Devuelve el diccionario
completo con valores por defecto, y vas rellenando de uno en uno:

```python
from urllib.parse import urlparse
import tldextract

def analizar_url(url: str) -> dict:
    partes = tldextract.extract(url)
    dominio = f"{partes.domain}.{partes.suffix}"

    return {
        "url": url,
        "edad_dominio_dias": None,
        "tld_riesgo": "bajo",
        "es_typosquat": False,
        "marca_suplantada": None,
        "es_acortador": False,
        "url_expandida": None,
        "deep_link": None,
    }
```

**Paso 2 — TLD de riesgo.** Es la más fácil y da mucho valor. Hay extensiones
que se regalan o cuestan céntimos, y ahí se concentra el fraude:

```python
TLD_ALTO  = {"zip", "mov", "top", "xyz", "click", "tk", "ml", "ga", "cf",
             "gq", "buzz", "rest", "country", "kim", "work", "link"}
TLD_MEDIO = {"info", "biz", "online", "site", "shop", "live", "icu"}

def riesgo_tld(suffix: str) -> str:
    if suffix in TLD_ALTO:  return "alto"
    if suffix in TLD_MEDIO: return "medio"
    return "bajo"
```

**Paso 3 — edad del dominio.** Un dominio registrado hace 3 días que dice ser
Correos es fraude casi seguro. Cuidado: `whois` devuelve cosas raras (a veces
una lista, a veces `None`), hay que blindarlo:

```python
import whois
from datetime import datetime, timezone

def edad_en_dias(dominio: str):
    try:
        creacion = whois.whois(dominio).creation_date
        if isinstance(creacion, list):      # a veces devuelve varias fechas
            creacion = creacion[0]
        if creacion is None:
            return None
        return (datetime.now() - creacion.replace(tzinfo=None)).days
    except Exception:
        return None      # muchos TLD no dan whois: no es un fallo tuyo
```

**Paso 4 — typosquatting.** Es tu tarea estrella. Tres trucos que usan los
malos, de más fácil a más difícil de pillar:

1. **Letra cambiada:** `correos.es` → `correros.es`, `bbva.es` → `bbwa.es`.
   Se detecta con distancia de edición (mira `difflib.SequenceMatcher`, que ya
   viene con Python, no hace falta instalar nada).
2. **Homoglifos:** letras que se parecen. `0`↔`o`, `1`↔`l`↔`i`, `rn`↔`m`.
   Normaliza esas letras antes de comparar.
3. **Marca en el subdominio** (el más usado y el que más engaña):
   `correos.es.pago-pendiente.top`. El dominio real es `pago-pendiente.top`,
   pero el usuario lee "correos.es" al principio y se fía. Compara la marca
   contra el **dominio real**, no contra la cadena entera.

Lista de marcas para empezar (las que más se suplantan en España):
```python
MARCAS = ["correos", "dgt", "aeat", "bbva", "santander", "caixabank",
          "sabadell", "seur", "dhl", "amazon", "netflix", "endesa",
          "iberdrola", "movistar", "vodafone", "seguridadsocial"]
```

**Paso 5 — acortadores.** Aquí sí tocas la red, pero **solo la cabecera**: pides
`HEAD`, que trae la respuesta sin descargar la página. Así ves a dónde lleva sin
ejecutar nada:

```python
import requests

ACORTADORES = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd",
               "rb.gy", "shorturl.at", "ow.ly", "acortar.link"}

def expandir(url: str):
    try:
        r = requests.head(url, allow_redirects=True, timeout=5)
        return r.url
    except Exception:
        return None
```

**Paso 6 — deep-links.** Si la "URL" no empieza por `http://` o `https://`, es
que intenta abrir otra app del móvil (Telegram, WhatsApp, una app de banco
falsa...). Eso es siempre sospechoso:

```python
esquema = urlparse(url).scheme
deep_link = url if esquema not in ("http", "https", "") else None
```

---

## Trampas conocidas

**`whois` tarda un montón o se cuelga**
Es normal, va contra servidores externos. Ponle siempre un `try/except` y no te
obsesiones: que devuelva `None` es una respuesta válida.

**`whois` no encuentra nada para un `.top` o un `.xyz`**
Muchos TLD baratos no dan datos públicos. Devuelve `None` y ya está — el motor
de Jose ya sabe tratar "no se pudo comprobar" como una sospecha leve.

**Te sale `es_typosquat = True` con webs legítimas**
Cuidado con esto, es lo peor que puede pasar: si marcas como fraude el banco de
verdad, la herramienta pierde toda la credibilidad. Ajusta el umbral de
parecido hasta que las webs buenas dejen de saltar.

---

## Cuando termines

```powershell
pytest tests/test_contratos.py -k analisis -v     # tiene que salir PASSED
git add .
git commit -m "analisis_url: whois, TLD de riesgo y typosquat"
git push origin feat/analisis-url-alex
```

Entra en GitHub → **"Compare & pull request"** → lo creas y Jose lo revisa.
