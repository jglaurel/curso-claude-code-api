---
name: segmentar-commits
description: Propone cómo repartir los cambios pendientes del árbol de trabajo en commits de una sola intención, con mensajes Conventional Commits, y espera aprobación antes de confirmar nada.
---

# Segmentar commits

Uso: `/segmentar-commits [criterio o alcance opcional]`

Esta skill propone un reparto de los cambios pendientes en commits. No
confirma ningún commit por su cuenta: el paso final siempre es mostrar la
propuesta y esperar aprobación explícita.

## 1. Partir del estado real del repositorio

Antes de proponer nada, ejecutar:

- `git status --porcelain=v1` — qué archivos están modificados, nuevos,
  eliminados o sin seguimiento, ahora mismo.
- `git diff --stat` y `git diff --cached --stat` — el resumen por archivo
  (rutas y líneas +/-) de lo no confirmado, tanto lo que está en staging
  como lo que no.

No se asume qué cambió a partir de la conversación previa, un plan en
`docs/`, o lo que "debería" haber — se lee el estado real en el momento de
invocar la skill. Si `git status` no muestra cambios pendientes, la skill
lo informa y termina: no hay nada que repartir.

**No se inyecta el diff completo (`git diff` sin `--stat`).** Solo el
resumen por archivo. El reparto en commits es una decisión de **qué archivo
o fragmento va con qué otro**, no de qué dice cada línea del código — el
mapa del cambio (qué rutas se tocaron, cuánto creció o encogió cada una)
alcanza para agrupar por intención. Si al planificar el reparto hace falta
ver el contenido de un archivo concreto para decidir si es separable (por
ejemplo, si un mismo archivo mezcla dos intenciones y hay que partirlo por
fragmento), se lee ese archivo puntual con `git diff -- <ruta>` o `Read` en
ese momento — no todo el diff por adelantado.

## 2. Repartir en commits de una sola intención

- Cada commit propuesto tiene **una sola intención**: un commit no mezcla,
  por ejemplo, una migración de base de datos con la ruta que la consume,
  ni una corrección de estilo con una funcionalidad nueva.
- El **orden** de los commits propuestos es el orden en que se confirmarían:
  cada commit, aplicado sobre el anterior, debe dejar el repositorio en un
  estado comprobable (el código importa, la suite no queda rota a medias
  por una dependencia que todavía no existe, una migración no referencia
  una tabla que un commit posterior crea). Si dos archivos deben ir juntos
  porque separarlos deja un estado intermedio roto, van en el mismo commit
  y se dice por qué.
- Cuando un mismo archivo mezcla más de una intención (crece a lo largo de
  varios commits propuestos), el reparto lo dice explícitamente y señala
  que hace falta staging por fragmento (`git add -p` o equivalente), no por
  archivo completo — no se asume que un archivo entero pertenece a un solo
  commit solo porque aparece una vez en `git status`.

## 3. Mensajes en Conventional Commits, por intención

- Cada mensaje sigue Conventional Commits (`tipo: descripción`, con
  `tipo` entre `feat`, `fix`, `docs`, `test`, `refactor`, `style`, `chore`,
  u otro tipo estándar aplicable).
- El prefijo se elige por **lo que el commit hace observable**, no por la
  extensión o carpeta del archivo. Un cambio en un archivo `.py` no es
  automáticamente `feat`: si solo reordena imports o aplica formato, es
  `style`; si solo agrega o corrige tests sin tocar comportamiento, es
  `test`; si es un archivo de configuración de la skill o del repo sin
  efecto en el comportamiento observable, es `chore`. El mismo criterio
  aplica a la inversa: un cambio en `docs/` que documenta un contrato
  nuevo no dejar de ser `docs` solo porque acompaña código.

## 4. Mostrar la propuesta y esperar aprobación

- La salida final es la lista de commits propuestos, cada uno con:
  - Los archivos (o fragmentos de archivo) que incluye.
  - El mensaje propuesto.
  - Si aplica, una nota breve de por qué ese archivo va ahí y no en otro
    commit (especialmente si el orden importa para dejar el repo
    comprobable en cada paso).
- Esta skill **no ejecuta `git add` ni `git commit`**. Presenta el reparto
  y se detiene. Solo tras la aprobación explícita del usuario se procede a
  confirmar los commits, y eso ocurre fuera de esta skill (en la
  conversación normal, no como parte de su procedimiento).

## Límites de esta skill

- No decide por su cuenta reescribir historia, hacer squash de commits ya
  confirmados, ni tocar commits anteriores al estado actual del árbol de
  trabajo — solo propone cómo confirmar lo pendiente.
- No ejecuta ningún commit sin aprobación explícita, ni siquiera si el
  reparto parece obvio.
- No modifica el contenido de los archivos para facilitar el reparto (no
  reordena código para que un `git add -p` sea más limpio); trabaja con el
  diff tal como está.
