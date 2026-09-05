# 🔷 Jose Luis — Núcleo, integración y liderazgo

> **Tus archivos:** `src/qreaper/sandbox.py`, `scoring.py`, `pipeline.py`
> **Tu rama:** `feat/nucleo-jose`
> **Tus tests:** `pytest tests/test_contratos.py -k "sandbox or scoring" -v` + `pytest tests/test_scoring.py -v`

---

## Qué llevas

Dos sombreros:

1. **El núcleo técnico**: abrir la URL sospechosa de forma segura (sandbox) y
   convertir todas las señales en una nota (scoring). Es la parte con más
   riesgo y la que decide si la herramienta acierta o no.
2. **La integración y el equipo**: montar el pipeline, revisar los PR de los
   otros cuatro y mergear a `main`.

---

## Estado actual

### ✅ Hecho y verificado (`feat/nucleo-jose`, pusheado)

**`sandbox.py`** — Chromium headless con perfil desechable (sin cookies ni
sesiones, así que aunque la web sea maliciosa no hay nada que robar), descargas
bloqueadas, permisos denegados, solo `http`/`https`, timeout de 20s. Devuelve
cadena de redirecciones completa (saltos HTTP 301/302 reconstruidos hacia atrás
desde la petición final + saltos por JavaScript), captura de pantalla y
detección de formularios de login — `input[type=password]` más heurística por
texto para los que lo esconden, también dentro de iframes. Ante cualquier fallo
devuelve el contrato entero con `error`, nunca revienta el pipeline.

**`scoring.py`** — modelo aditivo explicable: cada punto lleva su motivo en
lenguaje llano. Combos (typosquat+login, dominio nuevo+login, acortador+cambio
de dominio). Devuelve `detalle` con el desglose por señal para el informe de
JuanFran. Si el sandbox falló, lo dice y **no** devuelve SEGURO.

**Tests:** 11 en verde. `tests/test_scoring.py` fija la calibración con 8 casos
sacados de campañas reales, incluido el que más importa: *un banco legítimo
pidiendo login NO puede dar PELIGRO* (si el detector alarma con logins normales,
el usuario deja de hacerle caso y la herramienta no sirve).

**`sandbox.py` en Docker** — la detonación ya ocurre dentro de un contenedor
desechable (`docker/Dockerfile.sandbox`). `detonar()` elige motor solo:
contenedor si la imagen está construida, Chromium local si no. El resultado
trae una clave `aislamiento` (`"contenedor"` | `"navegador"`) para que el
informe pueda decir con qué nivel se analizó. Detalle abajo.

**`pipeline.py` a prueba de módulos a medias** — que Alex o JuanFran no hayan
terminado ya no tumba el análisis: cada etapa va envuelta, el fallo se apunta
en `resultado["errores"]` y la cadena sigue. **Esto desatasca a Ismael**: puede
montar la CLI hoy contra el pipeline de verdad y ver resultados reales de
decode + sandbox + scoring, con los huecos marcados.

### 🔜 Pendiente

- [ ] Ajustar los pesos del scoring con los resultados del dataset de JuanFran
- [ ] Revisar los PR de los cuatro y mergear (PR #1 de Andrés: 4 apaños pedidos)
- [ ] Prueba end-to-end: correo con QR → informe final ← *bloqueada hasta que
      estén `analisis_url` (Alex) e `informe` (JuanFran)*
- [ ] Guion y ensayo de la demo

---

## El sandbox en Docker

Antes el aislamiento era **a nivel de navegador**: perfil desechable, sin
descargas, solo http/https. Eso cubre el robo de sesión, pero **no un exploit
del propio Chromium** — si la web maliciosa revienta el navegador, está en la
máquina. Es justo el punto que los profesores van a mirar en la memoria:
"detonar en un entorno aislado" no es lo mismo que "abrirlo en mi portátil con
menos cookies".

Ahora hay dos motores y el resultado dice cuál se ha usado:

| | `"navegador"` (respaldo) | `"contenedor"` (por defecto) |
|---|---|---|
| Perfil desechable, sin cookies | ✅ | ✅ |
| Aguanta un exploit de Chromium | ❌ | ✅ |
| Límite de memoria y procesos | ❌ | ✅ 1 GB / 512 pids |
| Sin privilegios ni capabilities | ❌ | ✅ |

Cómo se lanza el contenedor (está en `detonar_en_docker()`):

```
--rm                              se destruye al terminar
--user pwuser                     nada de root
--cap-drop ALL                    sin capabilities
--security-opt no-new-privileges  no puede escalar
--memory 1g --pids-limit 512      ni bomba de memoria ni fork bomb
```

Como el contenedor sí tiene salida a internet (la necesita para detonar), se
añadió un corte de **red interna**: antes de abrir nada se resuelve el host y
si cae en `127.x`, `192.168.x`, `10.x`, `169.254.169.254`... se rechaza. Así un
QR no nos puede usar de trampolín hacia la red de dentro. Escotilla para
laboratorios propios: `QREAPER_PERMITIR_RED_PRIVADA=1`.

**Construir la imagen** (una vez, tarda porque baja ~2 GB):

```
python -m qreaper.sandbox --construir-imagen
```

**Probar a mano:**

```
python -m qreaper.sandbox https://b-dev.es
python -m qreaper.sandbox https://b-dev.es --motor local
```

Si no tienes Docker no pasa nada: baja a Chromium local solo y los tests de
contenedor se saltan.

---

## Tu trabajo de lead (esto es la mitad del proyecto)

**El reparto está pensado para que nadie dependa de nadie.** Los contratos de
`CONTRATOS.md` son lo que permite que los cinco trabajemos a la vez. Si alguien
cambia una firma por su cuenta, se rompe.

**Cada uno tiene su test con su nombre.** No revises a ojo si alguien ha
terminado: mira si su test está verde. Eso te ahorra horas y a ellos les da una
diana clara.

**Cada uno tiene su hoja de ruta** en `docs/equipo/`, con su contrato, sus
tareas, código de arranque y las trampas típicas ya resueltas. Si uno pregunta
algo que está ahí, mándalo al archivo — que se acostumbren a buscarlo.

**Ojo con el cuello de botella:** Ismael depende de que los otros tres acaben.
En su archivo le he dejado cómo trabajar con datos de mentira para que no se
quede parado esperando. Recuérdaselo si le ves atascado.

---

## Recordatorios de gestión

- Invitados al repo: Alex (`Alexsm222`) y Andrés (`Andres-Caso-Iglesias`).
- **Faltan Ismael y JuanFran**: la API de GitHub solo invita por usuario, pero
  la web sí acepta email → https://github.com/bdjoseluis/qreaper/settings/access
- Importar `docs/monday-qreaper.xlsx` en Monday. Invita antes a los cuatro al
  tablero y así puedes mapear *Responsable* → **People** y las tarjetas caen
  asignadas solas.
- Pegar los enlaces de Drive y Monday en `docs/ORGANIZACION.md`.
- Proteger `main` es de pago en repos privados. Con la norma "todo por PR" vale,
  ya que revisas tú los merges.
