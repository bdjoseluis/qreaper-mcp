# 🔷 Andrés — Decode (sacar el QR y la URL)

> **Tu archivo:** `src/qreaper/decode.py`
> **Tu rama:** `feat/decode-andres`
> **Tu test:** `pytest tests/test_contratos.py -k decode -v`

---

## Qué haces tú

Eres la **puerta de entrada** del proyecto. Te llega un archivo (un correo, un
PDF o una foto) y tienes que encontrar el código QR que hay dentro y decirnos a
qué dirección apunta. Todo lo demás del programa arranca con lo que tú devuelvas.

```
correo.eml / factura.pdf / foto.png  ──►  TÚ  ──►  ["https://correos-es.top/pago"]
```

Llevas el módulo con más chicha de programación porque eres el que viene de DAM.

---

## Antes de nada

Si todavía no has montado el proyecto: **[`ARRANCA-AQUI.md`](../../ARRANCA-AQUI.md)**.
Son 10 minutos de copiar y pegar. Vuelve aquí cuando `pytest` te funcione.

Luego instala tus librerías (con el entorno activado, o sea con `(.venv)` delante):

```powershell
pip install pyzbar opencv-python pillow pdf2image
```

---

## Tu contrato (esto NO se toca sin avisar)

```python
def decode(ruta_archivo: str) -> list[str]:
    ...
```

- **Recibe:** la ruta de un archivo, como texto.
- **Devuelve:** una **lista de textos** con las URLs de los QR que hayas encontrado.
- **Sin repetidos.** Si el mismo QR sale 3 veces, va una sola vez.
- Si no hay ningún QR → devuelves lista vacía `[]`, **no** un error.

```python
>>> decode("datasets/legitimos/ejemplo.png")
['https://b-dev.es/']
```

---

## Tus tareas

### Sprint 0 — Setup (hasta el 10 ago)
- [ ] Clonar el repo y montar el entorno
- [ ] Cambiar a tu rama y ejecutar tu test (tiene que fallar diciendo tu nombre)

### Sprint 1 — Tu módulo (11–24 ago)
- [ ] **Decodificar un QR de una imagen** ← empieza por aquí, es la base
- [ ] Detectar el tipo de archivo (`.eml` / `.pdf` / imagen)
- [ ] Parsear correos `.eml` y sacar las imágenes adjuntas
- [ ] Sacar las imágenes de un PDF
- [ ] Preprocesar imágenes malas (torcidas, oscuras, con poca calidad)
- [ ] Soportar QR partidos o anidados
- [ ] Devolver la lista de URLs sin repetidos

### Sprint 2 — Integración (25 ago–1 sep)
- [ ] Probar con correos de verdad y ajustar lo que falle

### Sprint 3 — Memoria (2–5 sep)
- [ ] Escribir tu parte de la memoria: cómo se decodifica e ingiere

---

## Por dónde empezar (el orden importa)

**Paso 1 — que funcione con una imagen suelta.** Con esto ya tienes media tarea:

```python
from pyzbar.pyzbar import decode as leer_qr
from PIL import Image

def decode(ruta_archivo: str) -> list[str]:
    urls = []
    for codigo in leer_qr(Image.open(ruta_archivo)):
        urls.append(codigo.data.decode("utf-8"))
    return list(dict.fromkeys(urls))   # quita repetidos sin desordenar
```

Pruébalo con `datasets/legitimos/ejemplo.png` (apunta a `https://b-dev.es/`).

**Paso 2 — según el tipo de archivo.** Mira la extensión y ramifica:

| Extensión | Qué hacer |
|---|---|
| `.png .jpg .jpeg .webp .bmp` | Directo, como el paso 1 |
| `.pdf` | `pdf2image.convert_from_path()` te da una imagen por página |
| `.eml` | Módulo `email` (viene con Python, no se instala) |

Para el correo, el esqueleto es este:

```python
import email, email.policy

with open(ruta_archivo, "rb") as f:
    mensaje = email.message_from_binary_file(f, policy=email.policy.default)

for parte in mensaje.walk():
    if parte.get_content_maintype() == "image":
        datos = parte.get_payload(decode=True)   # los bytes de la imagen
        # guarda esos bytes en un archivo temporal y pásaselos a pyzbar
```

**Paso 3 — imágenes de mala calidad.** Aquí entra OpenCV. Si `pyzbar` no
encuentra nada a la primera, reintenta con la imagen tratada:

```python
import cv2

img = cv2.imread(ruta)
gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, umbral = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
# vuelve a intentar leer el QR con 'umbral'
```

Otro truco que funciona muy bien: **agrandar la imagen** (`cv2.resize` al doble)
antes de leerla. Muchos QR de correo vienen diminutos.

---

## Trampas conocidas (te van a pasar, no te asustes)

**`ImportError` raro de `pyzbar` con algo de `libzbar` en Windows**
Te falta el runtime de Visual C++. Instala https://aka.ms/vs/17/release/vc_redist.x64.exe
y reinicia la consola. Es el fallo número 1 de esta librería.

**`pdf2image` dice que no encuentra `poppler`**
`pdf2image` es solo el envoltorio, necesita Poppler aparte. Bájalo de
https://github.com/oschwartz10612/poppler-windows/releases, descomprime, y añade
la carpeta `bin` al PATH (o pásale `poppler_path="C:\\ruta\\bin"` a la función).

**El QR se lee pero la URL sale con caracteres raros**
Los QR no siempre son UTF-8. Usa `codigo.data.decode("utf-8", errors="replace")`.

---

## Cuando termines

```powershell
pytest tests/test_contratos.py -k decode -v     # tiene que salir PASSED
git add .
git commit -m "decode: leo QR de imágenes y PDF"
git push origin feat/decode-andres
```

Entra en GitHub → te sale el botón **"Compare & pull request"** → lo creas y
Jose lo revisa.

**No subas nada que no pase tu test.** Y si te atascas más de un rato, al grupo:
mejor preguntar que perder una tarde.
