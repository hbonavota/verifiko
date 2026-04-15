# Verification Result Contract

## 1. Problema a resolver

Actualmente Verifiko genera resultados de verificación ricos en señales, score, explicación y trazabilidad, pero el contrato real del sistema no está completamente fijado entre backend, persistencia y frontend.

Hoy existen varias tensiones:

- el backend expone más campos de los que realmente persiste
- parte de la explainability no es durable entre creación y recuperación posterior
- el frontend no consume todo el contrato del backend y en algunos casos sintetiza narrativa propia
- no está definido qué partes del resultado son contractuales y cuáles son solo presentacionales
- no está definido si una verificación histórica debe conservar exactamente el mismo resultado explicativo que tuvo al crearse

Esto genera riesgo de:

- inconsistencias entre POST y GET
- pérdida de auditabilidad
- drift entre backend y frontend
- regresiones silenciosas en explainability
- confianza reducida en el producto

---

## 2. Objetivo

Definir de forma explícita y verificable el contrato de una verificación de URL en Verifiko para que exista una única fuente de verdad entre:

- creación de verificación
- persistencia
- recuperación posterior
- renderizado frontend

La spec debe dejar cerrado:

- qué campos forman parte del resultado oficial
- cuáles son obligatorios
- cuáles deben persistirse
- cuáles pueden reconstruirse
- cuáles son durables
- cuáles puede usar el frontend
- cuáles no deben ser inventados o reinterpretados por el frontend

---

## 3. Alcance

### Incluido

- contrato del resultado de verificación expuesto por backend
- definición de campos obligatorios y opcionales
- definición de durabilidad por campo
- reglas entre respuesta de creación y respuesta de recuperación
- reglas de persistencia vs reconstrucción
- reglas de consumo frontend
- criterios de aceptación verificables
- casos de test del contrato

### No incluido

- rediseño visual del frontend
- cambios de scoring
- cambios de analizador o stage order
- refactor de arquitectura
- cambios de quota
- cambios de auth
- billing / Stripe / planes
- redacción final de textos de marketing
- especificación detallada del pipeline de análisis
- export/reporting externo

---

## 4. Definiciones

### Verificación
Resultado de analizar una URL objetivo y producir:

- señales detectadas
- score
- nivel de riesgo
- veredicto
- explicación
- metadatos de trazabilidad
- ownership

### Contrato del resultado
Conjunto de campos que el sistema promete devolver de forma estable a clientes internos o frontend.

### Campo durable
Campo que debe sobrevivir entre la creación y la recuperación posterior de una verificación.

### Campo reconstruible
Campo que puede recalcularse o regenerarse a partir de datos persistidos sin alterar el significado funcional del resultado.

### Campo presentacional
Campo que existe solo para UX/renderizado y no forma parte del núcleo auditable del resultado.

---

## 5. Reglas de negocio

### RB-1
Cada verificación debe tener un identificador único e inmutable.

### RB-2
Cada verificación debe almacenar el input original y una representación normalizada/redactada apta para persistencia.

### RB-3
El resultado oficial de una verificación debe incluir siempre, como mínimo:

- id
- is_owned
- original_input
- normalized_input
- status
- signals
- risk_assessment
- created_at
- updated_at
- calculation_version

### RB-4
El frontend no puede inventar contenido analítico que contradiga o sustituya el resultado oficial del backend.

### RB-5
Si un campo del resultado no está garantizado por backend, el frontend no debe presentarlo como si fuera parte del resultado oficial.

### RB-6
La recuperación posterior de una verificación debe devolver un resultado semánticamente consistente con el resultado generado al crearla.

### RB-7
Los campos marcados como durables deben estar disponibles tanto en la respuesta del POST de creación como en la respuesta del GET posterior.

### RB-8
Los campos reconstruibles solo podrán reconstruirse si:
- la reconstrucción está definida explícitamente en esta spec
- el significado funcional no cambia
- la reconstrucción no depende de datos externos no persistidos

### RB-9
Los campos presentacionales del frontend deben derivarse exclusivamente de:
- campos oficiales del backend
- reglas explícitas de presentación documentadas
y nunca de suposiciones implícitas del frontend.

### RB-10
La propiedad (`is_owned`) debe formar parte del contrato oficial del resultado.

### RB-11
Una verificación puede cambiar mientras su ciclo de vida no haya finalizado.

Reglas:

- mientras `status` sea `pending`, el sistema puede completar o fallar la verificación
- una vez `status` sea `completed` o `failed`, el resultado contractual debe considerarse cerrado
- desde ese momento no deben mutar los campos durables del resultado, salvo migración/versionado explícito documentado

---

## 6. Fuente de verdad

La fuente de verdad del resultado de una verificación es el backend.

Más concretamente:

- el backend define el shape oficial del resultado
- la persistencia define qué partes del resultado son durables
- el frontend solo presenta ese resultado
- el frontend no redefine el significado del resultado

---

## 7. Contrato oficial del resultado

## 7.1 Campos top-level obligatorios

```json
{
  "id": "string",
  "is_owned": "boolean",
  "original_input": "string",
  "normalized_input": "string",
  "status": "string",
  "signals": [],
  "risk_assessment": {},
  "created_at": "datetime",
  "updated_at": "datetime",
  "calculation_version": "string"
}
```

## 7.2 Campos top-level no garantizados en esta spec

Estos campos pueden aparecer en respuestas del backend, pero en esta spec no forman parte del contrato garantizado ni del contrato durable exigible de recuperación histórica.
```json
{
  "trace": [],
  "score_breakdown": []
}
```


## 8. Contrato de campos

### 8.1 Top-level

#### `updated_at`
- tipo: datetime
- obligatorio: sí
- durable: sí
- reconstruible: no

#### Regla sobre `updated_at`

- `updated_at` refleja la última mutación persistida del registro de verificación
- mientras la verificación esté en `pending`, `updated_at` puede cambiar
- una vez la verificación pase a `completed` o `failed`, `updated_at` no debe volver a cambiar por modificaciones del resultado contractual, salvo migración/versionado explícito
- el hecho de que `updated_at` exista no implica que el resultado histórico pueda reinterpretarse o recalcularse silenciosamente

#### `id`
- tipo: string
- obligatorio: sí
- durable: sí
- reconstruible: no

#### `is_owned`
- tipo: boolean
- obligatorio: sí
- durable: no como valor absoluto persistido; sí como propiedad contractual derivable
- reconstruible: sí, solo desde contexto de usuario autenticado + ownership persistido
- decisión de esta spec: debe tratarse como campo contractual obligatorio en toda respuesta, aunque su valor pueda derivarse en lectura
- si no existe contexto autenticado válido en lectura, `is_owned` debe devolverse como `false`
- `is_owned` no debe omitirse del contrato por ausencia de autenticación

#### `original_input`
- tipo: string
- obligatorio: sí
- durable: sí
- reconstruible: no
- longitud máxima contractual: 4096 caracteres

#### `normalized_input`
- tipo: string
- obligatorio: sí
- durable: sí
- reconstruible: no a efectos contractuales
- longitud máxima contractual: 4096 caracteres
- decisión de esta spec: debe tratarse como durable y oficial

#### Regla de redacción de input persistido

Los campos persistidos del resultado no deben conservar información sensible evitable en texto plano si existe una representación redacted/oficial suficiente para el contrato.

Como mínimo, esta spec exige que el contrato persistido no dependa de conservar credenciales embebidas, fragmentos o parámetros sensibles como condición para reconstruir el resultado oficial.

#### `status`
- tipo: enum
- valores válidos en esta spec: `pending`, `completed`, `failed`
- obligatorio: sí
- durable: sí
- reconstruible: no

#### `signals`
- tipo: lista
- obligatorio: sí
- durable: sí
- reconstruible: no en su totalidad semántica

#### `risk_assessment`
- tipo: objeto
- obligatorio: sí
- durable: sí
- parcialmente reconstruible: solo para subcampos marcados explícitamente

#### `trace`
- tipo: lista
- obligatorio: no
- durable: no garantizado en esta spec
- reconstruible: no desde frontend

#### `score_breakdown`
- tipo: lista u objeto
- obligatorio: no
- durable: no garantizado en esta spec
- reconstruible: solo si existe regla explícita backend futura

---

### 8.2 Contrato de `signals`

Cada señal oficial debe incluir como mínimo:

- `signal_type`
- `category`
- `severity`
- `confidence`
- `detected`
- `title`
- `description`
- `source`

Campos permitidos adicionales:

- `evidence`
- `message_key`
- `message_params`
- `base_weight`
- `tags`
- `created_at`

#### Reglas

- una señal persistida debe conservar su semántica entre POST y GET
- `title` y `description` no deben cambiar de significado entre creación y lectura
- `source` debe indicar origen analítico, no presentación
- el frontend puede ordenar o agrupar señales, pero no alterar su semántica

#### Regla de anclaje para UI

El frontend debe usar exclusivamente claves estables del contrato para mapeos lógicos de UI, tales como:

- `signal_type` como ancla principal
- `message_key` como clave de localización o render textual cuando aplique

Reglas:

- el frontend no debe depender de `title` o `description` para decidir iconos, colores, agrupaciones o comportamiento lógico
- `title` y `description` son contenido textual del resultado, no claves estables de comportamiento de UI
- si una señal requiere representación visual consistente, esta debe depender de un identificador contractual y no de texto libre

---

### 8.3 Contrato de `risk_assessment`

Debe incluir como mínimo:

- `score`
- `risk_level`
- `verdict`
- `summary`

#### Regla sobre `summary`

- `summary` es parte del resultado oficial
- `summary` debe conservar equivalencia semántica entre POST y GET
- no se exige equivalencia textual bit a bit en esta spec, pero sí equivalencia funcional
- el frontend no debe reemplazar `summary` por uno generado localmente si el backend lo entrega

Puede incluir además:

- `top_signals`
- `category_breakdown`
- `terminal_override_applied`
- `terminal_reason`
- `analysis_warnings`
- `analysis_trace`
- `explanation`

#### Reglas

- `score`, `risk_level`, `verdict` y `summary` son obligatorios y durables
- `top_signals` y `category_breakdown` deben ser durables
- `analysis_warnings`, `analysis_trace` y `explanation` deben clasificarse explícitamente como:
  - durables
  - reconstruibles
  - o no garantizados

#### Decisión de esta spec

Para esta primera versión, el sistema debe clasificar así:

##### Durables obligatorios

- `score`
- `risk_level`
- `verdict`
- `summary`
- `top_signals`
- `category_breakdown`
- `terminal_override_applied`
- `terminal_reason`

##### No garantizados todavía

- `analysis_warnings`
- `analysis_trace`
- `explanation`
- `score_breakdown`
- `trace` top-level

Esto significa que:

- backend no debe prometer estos últimos como parte durable del resultado histórico
- frontend no debe depender de ellos como si fueran persistentes y siempre disponibles

### 8.4 Regla de mínimos renderizables

Para que una verificación se considere conforme al contrato oficial, el backend debe poder devolver como mínimo un resultado renderizable compuesto por:

- identidad top-level obligatoria
- lista de señales oficiales, aunque esté vacía
- `risk_assessment.score`
- `risk_assessment.risk_level`
- `risk_assessment.verdict`
- `risk_assessment.summary`

Si faltan estos mínimos, la verificación debe considerarse contractualmente incompleta.

La existencia de un resultado mínimo renderizable no implica que todos los analizadores externos hayan respondido correctamente ni que la cobertura haya sido total.
---

## 9. Regla clave POST vs GET

### 9.1 Principio

La respuesta de creación (`POST /api/verifications`) y la respuesta de recuperación (`GET /api/verifications/{id}` owner-scoped o equivalente) deben ser semánticamente equivalentes en todos los campos durables.

### 9.2 Equivalencia obligatoria

Deben coincidir funcionalmente:

- `id`
- `original_input`
- `normalized_input`
- `status`
- `signals`
- `risk_assessment.score`
- `risk_assessment.risk_level`
- `risk_assessment.verdict`
- `risk_assessment.summary`
- `risk_assessment.top_signals`
- `risk_assessment.category_breakdown`
- `risk_assessment.terminal_override_applied`
- `risk_assessment.terminal_reason`
- `calculation_version`

### 9.3 No se exige equivalencia contractual todavía para

- `trace`
- `score_breakdown`
- `analysis_warnings`
- `analysis_trace`
- `explanation`

Hasta que exista una spec posterior de explainability durable.

---

## 10. Reglas de persistencia

### 10.1 Debe persistirse obligatoriamente

#### Verificación

- `id`
- `user_id`
- `original_input`
- `normalized_input`
- `status`
- `created_at`
- `updated_at`
- `calculation_version`

#### Signals

Debe persistirse como mínimo, para cada señal oficial persistida:

- `signal_type`
- `category`
- `severity`
- `confidence`
- `detected`
- `title`
- `description`
- `source`

Y además cualquier campo adicional que el sistema use para conservar fielmente la semántica oficial de la señal, tales como:

- `evidence`
- `message_key`
- `message_params`
- `base_weight`
- `tags`
- `created_at`

#### Risk assessment

- `score`
- `risk_level`
- `verdict`
- `summary`
- `top_signals`
- `category_breakdown`
- `terminal_override_applied`
- `terminal_reason`
- `calculated_at`
- `calculation_version`

### 10.2 No debe asumirse persistido

- `analysis_warnings`
- `analysis_trace`
- `explanation`
- `score_breakdown`
- `trace` top-level

Hasta que una spec posterior lo exija.

### 10.3 Regla de versionado

`calculation_version` es parte obligatoria del contrato y debe permitir identificar la versión lógica con la que fue calculado el resultado persistido.

Reglas:

- una verificación histórica debe conservar su `calculation_version`
- una recuperación posterior no debe recalcular silenciosamente el resultado con otra versión
- cualquier migración que altere semántica del resultado deberá tratarse como cambio explícito de versionado y no como reconstrucción implícita
---

## 11. Reglas de reconstrucción

### 11.1 Backend

El backend puede reconstruir campos no durables únicamente si:

- existe regla explícita
- la reconstrucción usa datos persistidos
- no altera el significado del resultado

### 11.2 Frontend

El frontend no debe reconstruir ni presentar como verdad oficial del motor:

- explanation oficial
- analysis trace oficial
- warnings oficiales
- score breakdown oficial
- decision trace oficial
- recommendation oficial
- evidence summary oficial

si esos campos no vienen del backend como contrato explícito.

Además:

- el frontend no debe usar adapters para reinterpretar el resultado de forma que cambie su significado analítico
- el frontend no debe fabricar narrativa analítica sustitutiva a partir de campos parciales
- cualquier síntesis de UI debe mantenerse claramente separada del resultado oficial

### 11.3 Frontend sí puede

- ordenar señales
- agrupar señales por categoría
- traducir labels UI
- colapsar/expandir bloques
- derivar estados visuales

pero no cambiar el relato analítico oficial ni presentar síntesis propias como verdad del motor.

---

## 12. Estados y errores

### 12.1 Estados válidos

- `pending`
- `completed`
- `failed`

#### Regla sobre análisis degradado

El estado `completed` incluye tanto:

- verificaciones completadas con cobertura total esperada
- verificaciones completadas con cobertura degradada, siempre que el sistema haya podido producir un resultado mínimo renderizable conforme a esta spec

Por tanto:

- un análisis degradado no implica automáticamente estado `failed`
- `failed` debe reservarse para casos en los que no pueda emitirse un resultado contractual mínimo
- la degradación de cobertura y el lifecycle state son dimensiones distintas

Si existen otros en código, deberán documentarse en una spec posterior de lifecycle.

### 12.2 Errores relevantes para esta spec

- verificación no encontrada
- verificación no accesible por ownership
- contrato parcial de campos no durables
- ausencia de campos opcionales no garantizados

### 12.3 Regla importante

La ausencia de campos no garantizados no debe romper el frontend.

---

## 13. Reglas de frontend

### 13.1 Permitido

- presentar señales oficiales
- presentar score/risk/verdict oficiales
- presentar summary oficial
- usar ownership oficial
- mostrar placeholders si faltan campos no garantizados
- construir ayudas visuales claramente etiquetadas como UI derivada

### 13.2 Prohibido

- inventar explanation oficial
- inventar decision trace oficial
- inventar evidence summary oficial
- inventar recommendation oficial
- presentar contenido sintetizado como si fuese backend truth

Si un campo oficial del backend existe en la respuesta y forma parte del contrato garantizado, el frontend debe priorizar ese campo oficial frente a cualquier síntesis, fallback o adaptación local.

### 13.3 Si se desea UI derivada

Debe etiquetarse claramente como:

- resumen UI
- interpretación visual
- ayuda de lectura

y además:

- no puede reemplazar campos oficiales del backend
- no puede presentarse como salida del motor
- no puede contradecir señales, score, verdict o summary oficiales

---

## 14. Riesgos

- romper compatibilidad entre POST y GET
- persistir menos de lo prometido
- que frontend siga dependiendo de campos no durables
- mantener drift entre tipos frontend y schemas backend
- introducir ambigüedad histórica sobre qué fue realmente evaluado
- erosionar la confianza del producto si la UI cuenta una historia diferente al motor

---

## 15. Supuestos

- el backend seguirá siendo la fuente de verdad del resultado
- la persistencia actual de señales y risk assessment base es suficiente para sostener una primera versión contractual
- la explainability completa durable se resolverá en una spec posterior
- ownership seguirá siendo enforced server-side
- el frontend puede adaptarse para dejar de sintetizar partes no contractuales

---

## 16. Criterios de aceptación

### AC-1
Toda verificación creada debe devolver los campos obligatorios definidos en esta spec.

### AC-2
Toda verificación recuperada por owner debe devolver los mismos campos durables con equivalencia semántica respecto al POST de creación.

### AC-3
El frontend no debe depender de `trace`, `score_breakdown`, `analysis_warnings`, `analysis_trace` o `explanation` como si fueran siempre persistentes.

### AC-4
Los tipos/frontend contracts deben alinearse con el contrato oficial del backend para todos los campos durables.

### AC-5
La documentación no debe afirmar que un campo es durable si no lo es.

### AC-6
El sistema debe distinguir explícitamente entre:

- durable
- reconstruible
- no garantizado

para cada bloque importante del resultado.

### AC-7
`is_owned` debe existir y funcionar como parte del contrato oficial.

### AC-8
Una verificación histórica no debe cambiar su `score`, `risk_level`, `verdict` o `summary` respecto a su versión creada, salvo migración/versionado explícito.

### AC-9
Si un campo no garantizado aparece en POST y no aparece en GET, el sistema seguirá considerándose conforme a esta spec.

### AC-10
El frontend debe tratar todos los campos no garantizados como opcionales y renderizarlos de forma defensiva, sin romper la experiencia ni asumir su presencia.

### AC-11
Si el backend devuelve `summary`, el frontend debe mostrar ese `summary` oficial o una presentación visual equivalente que no cambie su significado.

### AC-12
El sistema no debe recalcular silenciosamente una verificación histórica con una `calculation_version` distinta durante una lectura normal.

---

## 17. Casos de test

### 17.1 Happy paths

#### T-1
Crear una verificación válida devuelve:

- campos top-level obligatorios
- `signals` no vacíos o vacíos válidos
- `risk_assessment` con `score`, `risk_level`, `verdict` y `summary`

#### T-2
Recuperar la misma verificación por owner devuelve:

- mismo `id`
- mismo `normalized_input`
- mismo `score`
- mismo `risk_level`
- mismo `verdict`
- mismo `summary`
- mismas señales persistidas semánticamente

#### T-3
`is_owned` es `true` para el owner autenticado.

---

### 17.2 Error paths

#### T-4
Recuperar una verificación sin ownership devuelve error de acceso o not found según política vigente.

#### T-5
El frontend no rompe si faltan campos no garantizados como `trace` o `explanation`.

---

### 17.3 Edge cases

#### T-6
Una verificación con warnings de enriquecimiento no debe perder sus campos durables principales.

#### T-7
Una verificación con terminal override por blacklist debe conservar:

- `score`
- `verdict`
- `terminal_reason`

en lectura posterior.

#### T-8
Una verificación creada con redirects o análisis degradado no debe alterar su contrato durable al recuperarse.

#### T-9
Si backend reconstruye algún campo reconstruible, el resultado no debe contradecir los datos persistidos.

#### T-10
Si una verificación histórica se recupera posteriormente, debe conservar la misma `calculation_version` con la que fue creada.

#### T-11
Si el backend entrega `summary`, el frontend no debe sustituirlo por uno generado localmente como resultado oficial.

---

## 18. Open questions para la siguiente spec

Estas preguntas no bloquean esta spec, pero deben resolverse luego:

1. ¿`analysis_warnings` debe pasar a ser durable?
2. ¿`analysis_trace` debe persistirse completo?
3. ¿`score_breakdown` debe persistirse exacto?
4. ¿`trace` top-level debe existir siempre o desaparecer del contrato?
5. ¿`explanation` debe ser durable o regenerada?
6. ¿El frontend debe dejar de sintetizar `recommendation`, `evidence summary` y `decision trace` por completo?
7. ¿POST y GET deben ser bit-a-bit equivalentes o solo semánticamente equivalentes?

---

## 19. Decisión de esta spec

Para la versión actual del sistema, el contrato oficial y exigible de Verifiko será:

### Garantizado y durable o contractualmente estable

- identidad de la verificación
- ownership como campo contractual de respuesta
- input persistido/redactado
- señales oficiales persistidas
- score
- risk_level
- verdict
- summary
- top_signals
- category_breakdown
- terminal override metadata
- timestamps
- calculation version

### No garantizado todavía como durable

- `trace`
- `score_breakdown`
- `analysis_warnings`
- `analysis_trace`
- `explanation`

### Regla final

El frontend no debe presentar los campos no garantizados como si fueran verdad persistente del motor.