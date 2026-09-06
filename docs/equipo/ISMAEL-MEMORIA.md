# Memoria — Módulo 6: Interfaz (CLI) y Documentación

**Autor:** Ismael · **Módulo:** `src/qreaper/cli.py` · **Rama:** `feat/interfaz-ismael`

---

## 1. Objetivo del módulo

El módulo de interfaz no analiza nada: su única responsabilidad es **traducir**
el resultado que produce `pipeline` (un diccionario con señales, resultado de
sandbox, puntuación y motivos) en algo que una persona sin conocimientos
técnicos pueda entender de un vistazo. Esta separación es deliberada y está
fijada en `CONTRATOS.md`: ningún módulo de análisis conoce la existencia de la
CLI, y la interfaz no conoce cómo se calcula una nota de riesgo,
solo cómo mostrarla. Esto permite que los cinco módulos de análisis y el
módulo de interfaz se desarrollen y se prueben en paralelo sin bloquearse
entre sí.

```
archivo/URL → pipeline.analizar_archivo() / analizar_url_suelta()
            → dict {url, senales, sandbox, scoring, informe, errores}
            → [ TÚ ESTÁS AQUÍ ]  cli.py
            → veredicto legible para el usuario final
```

## 2. La CLI sobre el pipeline

| | CLI (`cli.py`) |
|---|---|
| Tecnología | `click` |
| Uso previsto | Automatización, scripts, integración en otras herramientas (`--json-out`) |
| Entrada | Ruta de archivo o URL por argumento |
| Formato salida | Terminal con color, o JSON crudo |

La CLI llama directamente a `qreaper.pipeline`, nunca reimplementa lógica.
Esto evita el problema típico de tener "dos versiones de la verdad": si mañana
cambia una regla de scoring, `cli.py` no necesita tocarse.

Se ha estructurado como un grupo de comandos (`qreaper <comando>`) en vez de un
único script, porque hay dos casos de uso distintos que conviene no mezclar:

- `qreaper analizar <archivo>` — pipeline completo desde un correo/PDF/imagen.
- `qreaper url <url>` — analiza una URL suelta, sin tener que fabricar un QR.
  Es también lo que se ha usado internamente para probar la cadena mientras
  los demás módulos aún no estaban terminados.

Decisiones de diseño relevantes:

- **Colores e iconos como codificación redundante del veredicto**
  (`⛔ PELIGRO` rojo, `⚠️ SOSPECHOSO` amarillo, `✅ SEGURO` verde). El objetivo
  es que el veredicto se entienda "desde lejos", sin leer texto — importante
  porque el usuario típico de esta herramienta no es un analista de
  seguridad. El color nunca es el único portador de información: siempre va
  acompañado de la palabra y del icono, por accesibilidad (daltonismo).
- **`--json-out` en ambos comandos.** Permite usar `qreaper` como pieza de
  otra automatización (`qreaper analizar x.eml --json-out | jq ...`) sin tener
  que parsear la salida "bonita" pensada para humanos.
- **Degradación visible, no silenciosa.** Cuando un módulo de análisis aún no
  está implementado o falla, `pipeline` no lanza una excepción: rellena
  `errores` y sigue con lo que sí tiene (contrato descrito en
  `pipeline.py`, función `_resguardo`). La CLI refleja esto mostrando un
  bloque de "Avisos" en amarillo con qué módulo ha fallado y por qué, en vez
  de fingir que el análisis está completo. Esto fue clave durante el Sprint 1:
  permitió tener la interfaz terminada y probada con un resultado de mentira
  (`FALSO` en `ISMAEL.md`) antes de que el resto de módulos existieran, y
  luego enchufarla sin cambios cuando fueron llegando.
- **Manejo de errores de usuario vs errores de programa.** Un archivo que no
  existe es un error esperable del usuario: `click.Path(exists=True)` lo
  detecta antes de llamar al pipeline y da un mensaje normal, sin traceback.
  Un fallo interno inesperado sí se registra con `log.exception` (solo visible
  con `-v`) y termina con código de salida `2`, para distinguir "el usuario se
  ha equivocado" de "hay un bug".
- **Resumen agregado al final** (`_pinta_resumen`) cuando un archivo trae
  varios QR: cuenta cuántos han caído en cada veredicto. Se añadió porque
  durante las pruebas con `phishing_multiples.eml` la salida por cada QR por
  separado no dejaba ver de un vistazo el resultado global del correo.

## 3. Por qué "la interfaz no analiza nada" es una regla y no una sugerencia

Es tentador, cuando se está montando la parte visual, añadir algún atajo:
por ejemplo, decidir en `cli.py` que si la nota es mayor de 80 el texto se
ponga en rojo aunque `scoring` no lo haya marcado como `PELIGRO`, o calcular
un resumen distinto al que da `pipeline`. Se ha evitado
explícitamente cualquier lógica de este tipo por dos motivos:

1. **Un solo sitio de verdad.** Si la interfaz decide algo por su cuenta y el
   informe (PDF/HTML) decide otra cosa distinta a partir de los mismos datos,
   el usuario recibe dos mensajes contradictorios sobre el mismo enlace.
2. **Trazabilidad para la memoria y para depurar.** Todo lo que se muestra
   sale literalmente de las claves que documenta `CONTRATOS.md`
   (`scoring.veredicto`, `scoring.nota`, `scoring.motivos`, `sandbox.*`,
   `errores`). Si el veredicto de una URL concreta parece raro, se puede
   reproducir con `qreaper url <url> --json-out` y ver exactamente qué señal
   ha pesado, sin tener que sospechar de la capa de presentación.

## 4. Limitaciones conocidas y trabajo futuro

- Queda pendiente una interfaz web sobre el mismo pipeline, para poder usar la
  herramienta sin abrir una terminal. No está implementada.
- La CLI no cachea resultados: analizar la misma URL dos veces
  vuelve a detonarla en el sandbox. Para un lote grande convendría un modo
  por lotes con caché por URL, fuera del alcance de este proyecto.
- La detección de accesibilidad se ha limitado a no depender solo del color;
  no se ha probado con lector de pantalla.

## 5. Cómo se ha probado

Sin pruebas automatizadas propias (el contrato de este módulo es de
presentación, no de lógica), la validación ha sido manual y sistemática con
los ficheros de `datasets/test/`:

- `phishing_correo.eml` y `phishing_documento.pdf` → veredictos `SOSPECHOSO`/`PELIGRO` visibles con un vistazo, motivos coherentes con las señales devueltas por `analisis_url` y `sandbox`.
- `legitimo_correo.eml` y `legitimo_documento.pdf` → veredicto `SEGURO`, sin avisos.
- `phishing_multiples.eml` → varios QR en un mismo correo, resumen final correcto.
- Archivo inexistente → mensaje de error normal, sin traceback, código de salida distinto de 0.
- Con los módulos de análisis aún sin terminar (antes de la integración) → bloque de "Avisos" visible en vez de un fallo silencioso o un crash.

El test `tests/test_smoke.py` cubre que `cli` importa sin errores como parte
de la comprobación general del entorno; no hay tests de contrato específicos
para `cli.py` porque no expone una función con firma fija en
`CONTRATOS.md` — su "contrato" es orquestar `pipeline`, ya cubierto por los
tests de `test_pipeline.py`.
