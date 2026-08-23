# 👋 Ismael — empieza por aquí (sin saber nada de GitHub)

Esto es para leer **antes** que [`ISMAEL.md`](ISMAEL.md). No hace falta que sepas
nada de programación ni de GitHub. Vamos poco a poco y sin usar la consola.

Si algo no te sale, escribe al grupo. En serio: preguntar aquí es normal, y
perder dos horas atascado es lo que no queremos.

---

## 1. ¿Qué es GitHub y por qué lo usamos?

Imagínate una **carpeta compartida** (tipo Drive) pero pensada para código, con
dos cosas que Drive no tiene:

- **Guarda todas las versiones.** Puedes volver a cómo estaba el proyecto ayer,
  o hace tres semanas. **Nada se pierde nunca.** Esto es importante que lo
  interiorices: por mucho que toques, no puedes romper el trabajo de nadie.
- **Cada uno trabaja en su copia.** A esa copia se le llama **rama**. Tú tienes
  la tuya (`feat/interfaz-ismael`), los demás la suya. Trabajáis a la vez sin
  pisaros, y al final se juntan.

Tres palabras que vas a oír todo el rato:

| Palabra | Qué significa de verdad |
|---|---|
| **repositorio** (repo) | La carpeta del proyecto |
| **rama** (branch) | Tu copia personal para trabajar sin molestar |
| **commit** | Guardar un punto de control ("aquí funcionaba") |
| **push** | Subir tus cambios a internet para que los veamos |
| **pull request** (PR) | "He acabado, revísame esto y júntalo con lo demás" |

Ya está. Eso es GitHub.

---

## 2. Créate la cuenta

1. Ve a **https://github.com/signup**
2. Usa tu correo: `Ismaelgutierrezserrano14@gmail.com`
   *(importante que sea ese, porque es al que Jose te ha invitado)*
3. Elige un nombre de usuario (el que quieras, se ve públicamente).
4. Confirma el correo.

**Pásale tu nombre de usuario a Jose por el grupo.**

---

## 3. Acepta la invitación

Busca en tu correo un mensaje de GitHub que dice algo como *"bdjoseluis invited
you to collaborate on bdjoseluis/qreaper"* → dale a **Accept invitation**.

A partir de ahí ya ves el proyecto en https://github.com/bdjoseluis/qreaper

Si no te llega, mira en Spam. Y si no está, avisa a Jose.

---

## 4. Instala GitHub Desktop (nada de consola)

Los demás usan comandos de texto. **Tú no tienes por qué.** GitHub Desktop hace
lo mismo con botones.

1. Descarga: **https://desktop.github.com**
2. Instala y entra con tu cuenta de GitHub.
3. **File → Clone repository** → pestaña *GitHub.com* → elige `qreaper` →
   guárdalo en `D:\qreaper` → **Clone**.

Ya tienes el proyecto en tu ordenador.

### Cambiarte a tu rama (esto hazlo SIEMPRE antes de tocar nada)

Arriba en el centro hay un botón que pone **Current branch: main**. Púlsalo y
elige **`feat/interfaz-ismael`**.

> ⚠️ Si pone `main`, **para**. Cámbiate a la tuya antes de tocar un archivo.
> Es la única regla que no se salta nadie.

### Guardar y subir tu trabajo

Cuando hayas cambiado algo, en GitHub Desktop:

1. Abajo a la izquierda escribe qué has hecho (ej: *"salida de consola con colores"*).
2. Botón **Commit to feat/interfaz-ismael**.
3. Arriba, botón **Push origin**.

Ya está subido. Eso es todo el proceso, siempre igual.

---

## 5. Para ver y editar el código

Instala **Visual Studio Code**: https://code.visualstudio.com
Ábrelo, **File → Open Folder** → `D:\qreaper`. Tu archivo es
`src/qreaper/cli.py`.

Cuando lo abras por primera vez te preguntará si quieres instalar la extensión
de Python: dile que sí.

---

## 6. Ahora sí, monta el proyecto

Sigue **[`ARRANCA-AQUI.md`](../../ARRANCA-AQUI.md)** desde el **paso 3** (los
pasos 1 y 2 ya los has hecho con GitHub Desktop).

Esa parte sí lleva consola, pero es copiar y pegar 4 líneas. En VS Code la
abres con **Terminal → New Terminal** y pegas ahí.

Cuando `pytest` te funcione, vete a tu hoja de ruta: **[`ISMAEL.md`](ISMAEL.md)**.

---

## 7. Lo que de verdad se espera de ti

No te agobies con la palabra "programar". Tu módulo es **el más visual y el
menos algorítmico** del proyecto: no tienes que inventar nada, tienes que hacer
que lo que calculan los demás **se entienda al mirarlo**.

Tu primera tarea de verdad es coger un bloque de código que ya está escrito en
tu hoja de ruta y adaptarlo. Copiar, pegar, ejecutar, ver qué sale, ajustar. Así
es como se aprende esto, no leyendo.

Y llevas la **documentación**, que no es el premio de consolación: es lo que
entrega el grupo y lo que lee el profesor. Que esté bien explicado vale nota.

---

## Chuleta de emergencia

| Me pasa esto | Hago esto |
|---|---|
| No sé si estoy en mi rama | GitHub Desktop, botón de arriba. Tiene que poner `feat/interfaz-ismael` |
| He tocado algo y no sé qué he roto | GitHub Desktop → pestaña *Changes* → clic derecho → **Discard changes**. Vuelve a como estaba |
| Me sale un error rojo larguísimo | Copia las **últimas 3 líneas** y pégalas en el grupo. Ahí está lo importante |
| No entiendo una palabra | Pregunta. Nadie nació sabiendo esto |
