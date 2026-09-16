---
name: redactor-pr
description: Redacta la descripción de una solicitud de cambios en cuatro secciones fijas (qué cambia, decisiones técnicas, cómo se comprueba, qué queda sin probar), a partir del contrato, el plan y el estado real de la rama. No publica ni abre nada por su cuenta.
---

# Redactor de PR

Uso: `/redactor-pr [rama o alcance opcional]`

Esta skill redacta la descripción de una solicitud de cambios (pull
request). No publica la rama, no abre el PR, no lo integra. Entrega el
texto de la descripción para revisión y espera aprobación antes de que
cualquier otro paso lo use.

## 1. Partir del estado real de la rama, no de la memoria de la conversación

Antes de redactar, reunir:

- `git log main..HEAD --oneline` (o el rango equivalente contra la rama
  base) — qué commits entran en el PR, en qué orden.
- `git diff main...HEAD --stat` — el resumen por archivo de todo lo que
  cambia acumulado.
- `docs/contrato-api.md` y, si existe, el `docs/plan-*.md` relacionado con
  el trabajo de la rama — para contrastar el código contra lo que el
  contrato exige y detectar qué queda fuera.
- Si la conversación actual ya tiene decisiones articuladas (una
  ambigüedad que se preguntó y se resolvió, una limitación que ya se
  documentó en un plan), se reutilizan tal cual en vez de re-derivarlas del
  diff — ahorra inferencia y evita contradecir lo ya decidido. Pero la
  skill no depende de tener esa conversación disponible: si no la hay, las
  cuatro secciones se completan igual leyendo el diff, el contrato y los
  mensajes de commit.

## 2. Redactar en cuatro secciones fijas

La descripción sigue siempre esta estructura, en este orden:

### Qué cambia

Resumen del comportamiento observable nuevo o modificado: endpoints,
migraciones, archivos de configuración o de skill. Se agrupa por commit o
por incremento cuando el PR cubre varios, no por archivo tocado.

### Decisiones técnicas tomadas

Cada decisión que no se sigue mecánicamente del contrato o del código
existente, con el porqué. Si una decisión fue una pregunta que se hizo y se
respondió durante el trabajo, se cita la respuesta tal como quedó resuelta
— no se repite la pregunta ni se deja en condicional. Si una decisión ya
quedó escrita en un `docs/plan-*.md`, se referencia en vez de reescribirla
desde cero.

### Cómo se comprueba

Los comandos ejecutables exactos que verifican el PR — los mismos que ya
declaró cada incremento como su comprobación, más la suite completa y el
linter si el PR agrupa varios incrementos. No se describe en prosa un
resultado esperado sin el comando que lo produce. Si hubo verificación
manual (ej. contra la API real), se dice qué se llamó y qué se observó,
no solo que "se probó".

### Qué queda sin probar

Toda brecha real entre lo implementado y lo que el contrato pediría, y toda
dependencia ausente que impide una prueba (una entidad que otro plan
todavía no crea, un caso que el incremento decidió posponer). Se distingue
explícitamente una limitación **declarada y con dueño** (queda escrita aquí
o en el plan, con qué trabajo futuro la cierra) de una que simplemente no
se hizo — esta sección no es un lugar para excusas sin seguimiento. Si no
queda ninguna brecha real, se dice explícitamente que no hay ninguna: la
sección no se omite ni se deja vacía sin decirlo.

## 3. Mostrar el texto y esperar aprobación

- La salida es el título propuesto y el cuerpo completo de la descripción,
  en el formato exacto que se pegaría en la solicitud de cambios.
- Esta skill **no ejecuta `git push`, `gh pr create` ni ningún comando que
  publique o integre nada**. Entrega el texto, se detiene, y solo tras
  aprobación explícita del usuario otro paso (fuera de esta skill) lo usa
  para abrir el PR.

## Límites de esta skill

- No decide por su cuenta publicar la rama ni abrir la solicitud de
  cambios — eso ocurre en la conversación normal, después de la
  aprobación, no como parte de este procedimiento.
- No inventa una comprobación que no exista: si un incremento no declaró
  cómo se verifica, la skill lo señala como hueco en vez de redactar un
  comando plausible.
- No decide por su cuenta que una brecha es aceptable — si el alcance de
  lo que queda sin probar no está ya resuelto por el plan o el contrato, se
  pregunta antes de escribirlo como si fuera una decisión tomada.
