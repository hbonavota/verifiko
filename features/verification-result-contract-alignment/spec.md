# Verification Result Contract Alignment

## 1. Problema a resolver

Ya existe una spec fuente de verdad para el contrato del resultado de verificación:

- `/features/verification-result-contract/spec.md`

Sin embargo, el sistema real todavía puede incumplir esa spec en tres planos distintos:

- backend: mappers, DTOs, schemas y persistencia pueden no reflejar exactamente el contrato durable definido
- frontend: los tipos pueden no estar alineados con el contrato oficial y seguir asumiendo campos no garantizados
- adapter/UI: puede seguir existiendo lógica que sintetice narrativa analítica no contractual a partir de datos parciales

El problema no es definir el contrato otra vez.  
El problema ahora es **hacer que el código real cumpla el contrato ya aprobado**.

Si no se corrige esto, seguirán existiendo riesgos de:

- drift entre spec y código
- drift entre backend y frontend
- falsos supuestos sobre qué campos son durables
- diferencias entre POST y GET en campos contractuales
- narrativa frontend que suplante la verdad del motor

---

## 2. Objetivo

Alinear backend y frontend con la spec:

- `/features/verification-result-contract/spec.md`

para que:

- los campos durables definidos en la spec sean efectivamente contractuales en el sistema real
- los campos no garantizados sean tratados como opcionales/no durables
- el frontend no invente contenido analítico oficial
- POST y GET sean semánticamente equivalentes en los campos durables exigidos

---

## 3. Alcance

### Incluido

- alineación del backend con el contrato durable aprobado
- revisión y ajuste de DTOs, mappers, schemas y persistencia relevantes
- alineación de tipos frontend con el contrato aprobado
- limpieza del adapter frontend para eliminar narrativa analítica no contractual
- validación de equivalencia semántica POST vs GET para campos durables
- tests de contrato backend y tests/validaciones frontend relevantes

### No incluido

- persistir explainability completa no durable
- convertir `trace`, `score_breakdown`, `analysis_warnings`, `analysis_trace` o `explanation` en campos durables
- rediseño visual del frontend
- cambios de scoring
- cambios de pipeline o stage order
- cambios de auth
- cambios de quota
- billing / Stripe / planes
- refactors amplios fuera del contrato
- cambios de copy de marketing

---

## 4. Dependencia explícita

Esta spec depende de:

- `/features/verification-result-contract/spec.md`

Si hay conflicto, la fuente de verdad es la spec base del contrato.

---

## 5. Objetivos concretos de alineación

### OA-1 Backend contractual
El backend debe devolver y sostener correctamente todos los campos definidos como durables o contractualmente estables en la spec base.

### OA-2 POST vs GET
Las respuestas de creación y recuperación owner-scoped deben ser semánticamente equivalentes en todos los campos durables definidos.

### OA-3 Frontend tipado
El frontend debe tipar como obligatorios los campos contractuales garantizados y como opcionales los no garantizados.

### OA-4 Frontend no inventivo
El frontend no debe presentar como verdad oficial del motor contenido analítico sintetizado localmente.

### OA-5 Adapter mínimo
El adapter frontend debe limitarse a:
- adaptación de shape
- normalización de datos
- helpers presentacionales permitidos

y no a reinterpretación analítica del resultado.

---

## 6. Reglas de negocio

### RB-1
La spec base del contrato es la fuente de verdad para decidir qué campos son:

- durables
- reconstruibles
- no garantizados

### RB-2
No se permite promover implícitamente a durable ningún campo marcado como no garantizado en la spec base.

### RB-3
No se permite degradar a opcional ningún campo marcado como obligatorio/contractual en la spec base.

### RB-4
POST y GET owner-scoped deben devolver equivalencia semántica en los campos durables exigidos, aunque no necesariamente equivalencia bit a bit.

### RB-5
Si el backend devuelve un campo oficial contractual, el frontend debe priorizar ese campo frente a cualquier fallback local.

### RB-6
El frontend no puede construir:
- explanation oficial
- recommendation oficial
- evidence summary oficial
- decision trace oficial

a partir de campos parciales si esos bloques no vienen del backend como parte contractual explícita.

### RB-7
Los campos no garantizados deben tratarse en frontend como opcionales y renderizarse de forma defensiva.

### RB-8
La alineación debe hacerse con cambios mínimos y controlados, sin refactors amplios fuera del alcance.

---

## 7. Alcance técnico detallado

### 7.1 Backend

Se debe auditar y ajustar, como mínimo, el conjunto de piezas que participan en el contrato del resultado:

- models de persistencia relevantes
- mappers persistencia → dominio
- mappers dominio → DTO
- DTOs de aplicación
- schemas de API
- use cases de creación/lectura si afectan el shape final
- tests de integración y/o contrato

### 7.2 Frontend

Se debe auditar y ajustar, como mínimo:

- tipos de verificación
- adapter de verificación
- componentes que renderizan resultado
- cualquier helper que sintetice narrativa analítica
- rendering defensivo para campos no garantizados

---

## 8. Campos contractuales a alinear obligatoriamente

Esta feature debe verificar explícitamente que backend y frontend respetan como contractuales los siguientes bloques:

### 8.1 Top-level obligatorios

- `id`
- `is_owned`
- `original_input`
- `normalized_input`
- `status`
- `signals`
- `risk_assessment`
- `created_at`
- `updated_at`
- `calculation_version`

### 8.2 `risk_assessment` durable obligatorio

- `score`
- `risk_level`
- `verdict`
- `summary`
- `top_signals`
- `category_breakdown`
- `terminal_override_applied`
- `terminal_reason`

### 8.3 No garantizados que deben tratarse como opcionales

- `trace`
- `score_breakdown`
- `analysis_warnings`
- `analysis_trace`
- `explanation`

---

## 9. Reglas backend

### 9.1 DTOs y schemas
Los DTOs y response schemas deben reflejar fielmente el contrato aprobado.

### 9.2 Persistencia
Debe persistirse como mínimo todo lo marcado como durable en la spec base.

### 9.3 No sobreprometer
El backend no debe modelar como contractual obligatorio un campo que la spec base clasifica como no garantizado.

### 9.4 POST vs GET
La respuesta del POST y la del GET owner-scoped deben mantener equivalencia semántica para:

- top-level obligatorios
- señales persistidas
- `risk_assessment` durable
- `calculation_version`

### 9.5 Ownership
`is_owned` debe seguir existiendo como campo contractual de respuesta y no debe omitirse.

---

## 10. Reglas frontend

### 10.1 Tipos
Los tipos frontend deben alinearse con el contrato aprobado:

- obligatorios para campos garantizados
- opcionales para campos no garantizados

### 10.2 Adapter
El adapter no debe fabricar bloques analíticos oficiales.

Permitido:
- renombrar shape
- adaptar null/undefined
- agrupar o preparar datos para UI
- normalizar estructuras
- derivar helpers puramente visuales

Prohibido:
- generar explanation oficial
- generar recommendation oficial
- generar evidence summary oficial
- generar decision trace oficial
- sustituir `summary` oficial por uno generado localmente

### 10.3 Rendering
Si faltan campos no garantizados, el frontend debe:

- no romper
- no asumir presencia
- no usar fallback narrativo que se presente como verdad del motor

### 10.4 Prioridad del backend
Si existe un campo oficial contractual en la respuesta backend, ese valor debe prevalecer sobre cualquier cálculo local.

---

## 11. Estados y errores

### 11.1 Estados dentro de esta feature
Esta feature no redefine lifecycle. Solo exige respetar:

- `pending`
- `completed`
- `failed`

según la spec base.

### 11.2 Errores relevantes
- mismatch entre DTO/schema y spec
- mismatch entre persistencia y spec
- mismatch entre POST y GET
- tipos frontend desalineados
- adapter frontend que inventa narrativa analítica
- rendering roto por ausencia de campos no garantizados

---

## 12. Riesgos

- tocar mapper backend y romper respuestas existentes
- introducir cambios de shape no intencionados
- dejar el frontend en un estado intermedio donde espere campos distintos
- eliminar demasiada lógica del adapter sin reemplazar el mínimo presentacional necesario
- arreglar POST pero no GET
- arreglar schemas pero no persistencia real
- hacer refactors amplios disfrazados de alineación contractual

---

## 13. Supuestos

- la spec base del contrato ya está suficientemente aprobada para implementarse
- no se intentará resolver en esta feature la durabilidad completa de explainability
- el backend actual ya persiste suficiente información para cumplir la primera versión contractual durable
- el frontend puede simplificarse sin perder funcionalidad esencial
- los cambios se harán de forma incremental y testeable

---

## 14. Criterios de aceptación

### AC-1
El backend debe devolver todos los campos top-level obligatorios definidos en la spec base.

### AC-2
El backend debe devolver como durables y contractuales en `risk_assessment` al menos:

- `score`
- `risk_level`
- `verdict`
- `summary`
- `top_signals`
- `category_breakdown`
- `terminal_override_applied`
- `terminal_reason`

### AC-3
La recuperación owner-scoped de una verificación debe mantener equivalencia semántica con la respuesta de creación para todos los campos durables.

### AC-4
Los tipos frontend deben reflejar correctamente:
- campos obligatorios garantizados
- campos opcionales no garantizados

### AC-5
El frontend no debe presentar como resultado oficial bloques analíticos generados localmente que no estén en el contrato backend.

### AC-6
Si `summary` viene del backend, el frontend debe usar ese `summary` oficial y no sustituirlo por uno inventado localmente.

### AC-7
La ausencia de `trace`, `score_breakdown`, `analysis_warnings`, `analysis_trace` o `explanation` no debe romper el frontend.

### AC-8
El código resultante no debe ampliar el alcance promoviendo a durable campos no garantizados.

### AC-9
La suite de tests relevante debe validar explícitamente el contrato durable entre POST y GET.

### AC-10
La implementación no debe introducir refactors grandes fuera del alcance definido.

---

## 15. Casos de test

### 15.1 Happy paths

#### T-1
Crear una verificación devuelve todos los campos top-level obligatorios del contrato.

#### T-2
Crear una verificación devuelve `risk_assessment` con todos los campos durables obligatorios definidos por la spec base.

#### T-3
Recuperar la misma verificación por owner devuelve equivalencia semántica en:
- top-level obligatorios
- señales
- `risk_assessment` durable
- `calculation_version`

#### T-4
`is_owned` existe siempre en la respuesta y se comporta correctamente según contexto autenticado.

---

### 15.2 Error paths

#### T-5
Si faltan campos no garantizados en GET, el frontend sigue renderizando sin romper.

#### T-6
Si el adapter recibe ausencia de `trace`, `score_breakdown`, `analysis_warnings`, `analysis_trace` o `explanation`, no fabrica narrativa oficial sustitutiva.

#### T-7
Si una verificación no pertenece al usuario, la política actual de acceso sigue funcionando sin romper el contrato de ownership.

---

### 15.3 Edge cases

#### T-8
Una verificación con terminal override conserva `terminal_override_applied` y `terminal_reason` entre POST y GET.

#### T-9
Una verificación con señales complejas conserva semánticamente las señales persistidas entre POST y GET.

#### T-10
`calculation_version` permanece estable entre creación y lectura histórica.

#### T-11
El frontend trata los campos no garantizados como opcionales en tipos y render.

#### T-12
El adapter no genera `recommendation`, `evidence summary`, `decision trace` o `explanation` oficial a partir de campos parciales.

---

## 16. Plan de implementación esperado

La implementación debe dividirse en pasos pequeños:

### Paso 1
Auditar backend real contra la spec base y localizar mismatches concretos.

### Paso 2
Corregir contrato backend:
- mappers
- DTOs
- schemas
- persistencia si aplica dentro del alcance

### Paso 3
Añadir o ajustar tests backend de contrato POST vs GET.

### Paso 4
Alinear tipos frontend con el contrato aprobado.

### Paso 5
Podar adapter frontend para eliminar narrativa analítica no contractual.

### Paso 6
Validar rendering defensivo de campos no garantizados.

### Paso 7
Revisar que no haya cambios fuera de alcance.

---

## 17. Open questions no bloqueantes

1. ¿Habrá que conservar algún nivel mínimo de adapter narrativo como UI derivada explícitamente etiquetada?
2. ¿`top_signals` y `category_breakdown` ya cumplen hoy equivalencia semántica real entre POST y GET o requerirán ajustes de persistencia?
3. ¿Existe alguna respuesta actual del frontend que dependa en silencio de `trace` o `score_breakdown`?
4. ¿Hay tests de integración suficientes para detectar drift futuro del contrato?
5. ¿Conviene añadir una capa de tests de contrato más explícita para frontend/backend?

---

## 18. Decisión de esta spec

Esta feature no amplía el contrato.

Esta feature solo obliga al sistema real a cumplir el contrato ya aprobado en:

- `/features/verification-result-contract/spec.md`

Regla final:

- primero se alinea backend con la spec
- luego se alinea frontend con ese backend
- luego se elimina cualquier narrativa analítica frontend que contradiga o suplante la verdad contractual del motor