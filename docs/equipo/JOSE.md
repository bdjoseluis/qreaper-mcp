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

### 🔜 Pendiente

- [ ] **Meter el sandbox en Docker** ← lo siguiente
- [ ] `pipeline.py`: manejar que un módulo falle sin tumbar el análisis entero
- [ ] Ajustar los pesos del scoring con los resultados del dataset de JuanFran
- [ ] Revisar los PR de los cuatro y mergear
- [ ] Prueba end-to-end: correo con QR → informe final
- [ ] Guion y ensayo de la demo

---

## Lo siguiente: Docker

Hoy el aislamiento es **a nivel de navegador**: perfil desechable, sin
descargas, solo http/https. Eso cubre el robo de sesión, pero **no un exploit
del propio Chromium** — si la web maliciosa revienta el navegador, está en la
máquina.

Es un punto que los profesores van a mirar en la memoria: "detonar en un entorno
aislado" no es lo mismo que "abrirlo en mi portátil con menos cookies".

`sandbox.py` está escrito para que meterlo en un contenedor sea **envolver, no
reescribir** — ver la nota `PENDIENTE` en la cabecera del archivo. El plan:
imagen basada en `mcr.microsoft.com/playwright/python`, contenedor sin red hacia
la LAN, usuario sin privilegios, y `detonar()` pasa a hablar con el contenedor
en vez de lanzar Chromium en local.

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
