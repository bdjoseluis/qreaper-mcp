# 🚀 Arranca aquí (guía para el equipo)

Esto es lo primero que tienes que hacer. **No hace falta saber Python** para
completar esta guía: es copiar y pegar. Tardas 10 minutos.

Si algo falla, mira el apartado **"Cuando algo peta"** del final. Si sigue
fallando → escribe al grupo, **no te quedes atascado tú solo**.

---

## 0. Lo que necesitas instalado

| Programa | Cómo comprobar que lo tienes | Dónde bajarlo |
|---|---|---|
| **Git** | `git --version` | https://git-scm.com/downloads |
| **Python 3.10 o superior** | `python --version` | https://www.python.org/downloads/ |

> ⚠️ Al instalar Python en Windows, marca la casilla **"Add Python to PATH"**.
> Si no lo hiciste, desinstálalo y vuelve a instalarlo marcándola.

---

## 1. Bájate el proyecto

Abre **PowerShell** y ejecuta esto línea a línea:

```powershell
cd D:\
git clone https://github.com/bdjoseluis/qreaper.git
cd qreaper
```

---

## 2. Cámbiate a TU rama

Cada uno trabaja en la suya. **Nadie toca `main`.**

| Quién | Tu rama |
|---|---|
| Andrés | `feat/decode-andres` |
| Alex | `feat/analisis-url-alex` |
| JuanFran | `feat/informe-juanfran` |
| Ismael | `feat/interfaz-ismael` |
| Jose Luis | `feat/nucleo-jose` |

```powershell
git checkout feat/TU-RAMA-AQUI
```

Comprueba que estás donde tienes que estar:

```powershell
git branch --show-current
```

---

## 3. Monta el entorno

Un "entorno virtual" es una carpeta donde se instalan las librerías del
proyecto sin ensuciarte el Python del ordenador. Se crea una vez:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Sabrás que ha funcionado porque te aparecerá **`(.venv)`** al principio de la
línea de la consola. **Cada vez que abras una consola nueva tienes que volver a
ejecutar esa segunda línea** (activar), pero la primera solo una vez.

Ahora instala lo básico:

```powershell
python -m pip install --upgrade pip
pip install -e .
pip install pytest
```

---

## 4. Comprueba que todo va

```powershell
pytest -v
```

Verás algo así:

```
tests/test_smoke.py::test_imports PASSED
tests/test_contratos.py::test_decode_devuelve_lista_de_urls FAILED
tests/test_contratos.py::test_analisis_url_devuelve_todas_las_senales FAILED
...
```

**Eso está BIEN.** ✅ El primero en verde significa que tu entorno funciona.
Los demás fallan porque los módulos todavía están vacíos: son exactamente el
trabajo que tenemos que hacer.

---

## 5. Instala solo las librerías de TU módulo

En `requirements.txt` están todas, pero no necesitas las de los demás. Instala
únicamente tu bloque:

```powershell
# Andrés (decode)
pip install pyzbar opencv-python pillow pdf2image

# Alex (análisis de URL)
pip install python-whois tldextract requests

# JuanFran (informe)
pip install reportlab jinja2

# Ismael (CLI)
pip install click

# Jose (sandbox)
pip install playwright
playwright install chromium
```

---

## 6. A trabajar

**👉 Tienes tu propia hoja de ruta.** Ahí está tu contrato, tus tareas, el
código para arrancar y las trampas típicas ya resueltas. Es lo único que
necesitas leer aparte de esto:

| | |
|---|---|
| Andrés | [`docs/equipo/ANDRES.md`](docs/equipo/ANDRES.md) |
| Alex | [`docs/equipo/ALEX.md`](docs/equipo/ALEX.md) |
| JuanFran | [`docs/equipo/JUANFRAN.md`](docs/equipo/JUANFRAN.md) |
| Ismael | [`docs/equipo/ISMAEL.md`](docs/equipo/ISMAEL.md) |
| Jose Luis | [`docs/equipo/JOSE.md`](docs/equipo/JOSE.md) |

Y el resumen de lo que hay que hacer:

1. **Lee [`CONTRATOS.md`](CONTRATOS.md).** Es lo más importante del repo: dice
   exactamente qué recibe y qué devuelve tu función. Si no lo respetas, tu
   trabajo no encaja con el de los demás.
2. Abre tu archivo en `src/qreaper/` y sustituye el `raise NotImplementedError`
   por tu código.
3. Lanza **solo tu test** hasta que se ponga verde:

   ```powershell
   pytest tests/test_contratos.py -k decode -v      # cambia "decode" por lo tuyo:
                                                    # decode | analisis | sandbox | scoring | informe
   ```
4. Cuando esté en verde, súbelo:

   ```powershell
   git add .
   git commit -m "decode: extraigo QR de imágenes"
   git push origin feat/TU-RAMA-AQUI
   ```
5. Entra en GitHub → te saldrá un botón **"Compare & pull request"** → dale,
   escribe qué has hecho y créalo. Jose lo revisa y lo mergea.

**Una tarea está HECHA cuando:** funciona + su test pasa + el PR está mergeado.

---

## 🔧 Cuando algo peta

**`python` no se reconoce como comando**
No marcaste "Add Python to PATH". Reinstala Python marcando la casilla.

**`Activate.ps1 no se puede cargar porque la ejecución de scripts está deshabilitada`**
Windows bloquea scripts por defecto. Ejecuta esto y repite:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**`ModuleNotFoundError: No module named 'qreaper'`**
No has activado el entorno (te falta el `(.venv)` en la consola) o no hiciste
`pip install -e .`.

**`pyzbar` da un error raro de DLL en Windows (`ImportError ... libzbar`)**
Te falta el runtime de Visual C++. Instálalo desde
https://aka.ms/vs/17/release/vc_redist.x64.exe y reinicia la consola.

**`pdf2image` falla diciendo que no encuentra `poppler`**
`pdf2image` necesita Poppler aparte. Bájalo de
https://github.com/oschwartz10612/poppler-windows/releases, descomprime y añade
su carpeta `bin` al PATH.

**He tocado algo y no sé qué he roto**
Nada es irreversible, estás en tu rama. Para tirar tus cambios locales:
```powershell
git checkout -- .
```

---

## 📍 Dónde está cada cosa

| Archivo | Para qué |
|---|---|
| [`CONTRATOS.md`](CONTRATOS.md) | **Léelo primero.** Qué recibe y devuelve cada módulo |
| [`docs/ORGANIZACION.md`](docs/ORGANIZACION.md) | Equipo, sprints, fechas y tus tareas |
| `src/qreaper/` | El código. Cada uno toca **solo su archivo** |
| `tests/test_contratos.py` | Tu test. En verde = tarea terminada |
| `datasets/` | QR de ejemplo para probar |
