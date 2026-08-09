# QReaper — Organización del equipo (tablero Monday)

Proyecto Máster Ciberseguridad · Evolve · Inicio **5-ago-2026** · Entrega objetivo **~5-sep-2026**

---

## 👥 Equipo y perfiles

| Persona | Perfil | Módulo asignado | Rama |
|---|---|---|---|
| **Jose Luis** | Ing. software / DAM-DAW | Núcleo: sandbox + scoring + pipeline + integración | `feat/nucleo-jose` |
| **Andrés** | DAM (programación) | Decode (ingesta + QR → URL) | `feat/decode-andres` |
| **Alex** | Telecomunicaciones | Análisis estático de URL | `feat/analisis-url-alex` |
| **JuanFran** | Telecomunicaciones | Informe + dataset | `feat/informe-juanfran` |
| **Ismael** | Redes / Telecomunicaciones | Interfaz (CLI/web) + docs | `feat/interfaz-ismael` |

**Criterio de reparto:** los 2 que más programan (Jose, Andrés) llevan los módulos con más algoritmo (núcleo y decode). Los de teleco van a lo más cercano a redes/infra y de menor carga algorítmica (análisis de dominios, informe con plantillas, interfaz).

---

## 🗂️ Estructura del tablero en Monday

Crea un tablero **"QReaper"** con estas **columnas de estado**:

`Backlog` → `Sprint actual` → `En curso` → `En revisión (PR)` → `Hecho`

Y agrupa las tarjetas por **Sprint** (grupos del tablero):

- **Grupo: Sprint 0 — Setup** (esta semana)
- **Grupo: Sprint 1 — Módulos funcionales**
- **Grupo: Sprint 2 — Integración**
- **Grupo: Sprint 3 — Pulido + demo + memoria**

Campos recomendados por tarjeta: **Responsable**, **Estado**, **Prioridad**, **Fecha límite**, **Rama/PR**.

### ⬆️ Importar el tablero de golpe (54 tarjetas)

En vez de crear las tarjetas a mano, súbelas con el fichero ya preparado:

- Excel: [`monday-qreaper.xlsx`](monday-qreaper.xlsx)
- CSV (por si el Excel da guerra): [`monday-qreaper.csv`](monday-qreaper.csv)

Pasos en Monday:

1. Tablero nuevo → **Add** (o los 3 puntos del tablero) → **Import data** → **Excel/CSV**.
2. Sube el fichero y marca que **la primera fila son las cabeceras**.
3. Mapea las columnas así:
   - `Tarea` → **Item Name** (nombre de la tarjeta)
   - `Grupo` → **Group** (así te crea solo los 4 sprints)
   - `Responsable` → **People** *(si aún no están todos en Monday, mapea a **Text** y lo cambias luego)*
   - `Estado` → **Status** · `Prioridad` → **Status** o **Dropdown**
   - `Fecha límite` → **Date** · `Rama`, `Módulo`, `Notas` → **Text**
4. Importar. Repasa que los estados hayan cogido los colores (Backlog / En curso / Hecho).

---

## 📅 Sprints

| Sprint | Fechas | Objetivo |
|---|---|---|
| **0 — Setup** | 5–10 ago | Repo clonado, entorno montado, cada uno el "hola mundo" de su módulo |
| **1 — Módulos** | 11–24 ago | Cada módulo funciona por separado (pasa sus pruebas) |
| **2 — Integración** | 25 ago–1 sep | Todo encaja vía `pipeline`, dataset listo, informe real |
| **3 — Pulido** | 2–5 sep | Demo montada, memoria escrita, últimos bugs |

---

## ✅ Tareas por persona (copiar como tarjetas en Monday)

### 🔷 Jose Luis — Núcleo + Lead
**Sprint 0**
- [ ] Repo, estructura y contratos (hecho ✅)
- [ ] Dar acceso a colaboradores y proteger `main`
**Sprint 1**
- [ ] Sandbox: Playwright headless dentro de Docker
- [ ] Seguir redirecciones + capturar URL final
- [ ] Screenshot de la página de destino
- [ ] Detectar formularios de login
- [ ] Motor de scoring (señales → nota 0-100 + veredicto)
**Sprint 2**
- [ ] Integrar los 6 módulos en `pipeline`
- [ ] Revisar los PR de todos y mergear

### 🔷 Andrés — Decode (`decode.py`)
**Sprint 0**
- [ ] Clonar, montar entorno, ejecutar el stub
**Sprint 1**
- [ ] Parsear correos `.eml` y extraer imágenes
- [ ] Extraer imágenes de PDF (pdf2image)
- [ ] Decodificar QR de una imagen (pyzbar/OpenCV)
- [ ] Preprocesar imágenes de baja calidad (enderezar, limpiar)
- [ ] Soportar QR partidos / anidados
- [ ] Devolver lista de URLs únicas

### 🔷 Alex — Análisis de URL (`analisis_url.py`)
**Sprint 0**
- [ ] Clonar, montar entorno, ejecutar el stub
**Sprint 1**
- [ ] Edad y datos del dominio (whois)
- [ ] Clasificar TLD por riesgo
- [ ] Detectar typosquatting / homoglifos vs lista de marcas
- [ ] Expandir acortadores (bit.ly → destino real)
- [ ] Detectar deep-links (`telegram://`, `intent://`)
- [ ] Devolver diccionario de señales

### 🔷 JuanFran — Informe + Dataset (`informe.py`)
**Sprint 0**
- [ ] Clonar, montar entorno, ejecutar el stub
**Sprint 1**
- [ ] Plantilla de informe (PDF con reportlab)
- [ ] Versión JSON y HTML
- [ ] Volcar: URL + señales + screenshot + nota + recomendación
**Sprint 2**
- [ ] Informe de ejemplo para la demo

### 🔷 Ismael — Interfaz + Docs (`cli.py`)
**Sprint 0**
- [ ] Clonar, montar entorno, ejecutar el stub
**Sprint 1**
- [ ] CLI: `qreaper analizar imagen.png` → veredicto en consola
- [ ] Formatear la salida por consola (colores, claridad)
**Sprint 2**
- [ ] Web simple: subir imagen/email → ver resultado
- [ ] Documentar cómo se ejecuta todo (para la memoria)

---

## 🔒 Reglas de trabajo (Definition of Done)

1. **Cada uno en SU rama.** Nadie toca `main` directo.
2. Al terminar una tarea → **Pull Request** → Jose revisa → merge.
3. Antes de picar código: **leer `CONTRATOS.md`**. No cambiar una firma sin avisar.
4. Una tarea está "Hecha" solo cuando: funciona + su test pasa + PR mergeado.
5. Dudas → grupo de WhatsApp; bloqueos → avisar YA, no esperar.

---

## 🔗 Enlaces

- Repo: https://github.com/bdjoseluis/qreaper
- Contratos entre módulos: [`CONTRATOS.md`](../CONTRATOS.md)
- Drive compartido: *(pegar enlace)*
- Tablero Monday: *(pegar enlace)*
