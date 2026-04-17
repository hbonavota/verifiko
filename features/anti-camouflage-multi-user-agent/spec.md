# Anti-Camouflage Multi User-Agent Detection

## 1. Problema a resolver

Algunas URLs maliciosas sirven contenido distinto según el visitante para evadir análisis automáticos.

Ejemplos típicos:

- muestran una página benigna a bots o escáneres
- muestran phishing real solo a navegadores móviles
- muestran contenido distinto a desktop vs mobile
- muestran una página vacía o neutra a user agents sospechosos

Actualmente Verifiko realiza fetch y análisis HTML sobre una única variante de request, lo que deja una superficie de evasión importante.

Esto genera riesgo de:

- falsos negativos
- detección incompleta
- análisis no representativo del comportamiento real del target
- pérdida de ventaja frente a competidores con técnicas anti-evasión

---

## 2. Objetivo

Detectar variaciones sospechosas de contenido servidas por una misma URL cuando se consulta usando múltiples User-Agent.

El sistema debe:

- ejecutar múltiples fetches del mismo target con distintos User-Agent
- comparar los resultados obtenidos
- detectar divergencias relevantes
- emitir señales oficiales cuando exista indicio de camuflaje/evasión
- no romper el contrato actual del resultado de verificación

---

## 3. Alcance

### Incluido

- múltiples fetches HTTP del mismo target con distintos User-Agent
- comparación de respuestas HTML
- nueva señal contractual de anti-camuflaje si corresponde
- warnings de análisis si no puede completarse alguna variante
- integración mínima en el pipeline actual
- tests unitarios e integración relevantes

### No incluido

- análisis visual con screenshots
- ejecución JavaScript con navegador headless
- Playwright / Puppeteer / Selenium
- almacenamiento completo de snapshots HTML
- cambios de scoring amplios fuera de la nueva señal
- cambios de frontend no necesarios para mostrar la nueva señal
- nuevos endpoints

---

## 4. Objetivo funcional concreto

El sistema debe intentar al menos estas variantes de request para HTML:

- desktop browser
- mobile browser
- googlebot-like requester

Y debe comparar la respuesta entre variantes para detectar divergencia significativa.

---

## 5. Reglas de negocio

### RB-1
La verificación debe seguir siendo síncrona en esta feature.

### RB-2
La nueva lógica no debe alterar el contrato durable actual del resultado.

### RB-3
La ausencia o fallo de una variante de fetch no debe hacer fallar toda la verificación si todavía puede emitirse un resultado contractual mínimo.

### RB-4
Solo debe emitirse una señal de anti-camuflaje cuando la divergencia entre variantes sea suficientemente significativa y no explicable por diferencias triviales.

### RB-5
No se debe considerar camuflaje únicamente por diferencias menores como:
- timestamps
- tokens efímeros
- nonces
- pequeños cambios cosméticos
- orden irrelevante de atributos

### RB-6
La comparación debe basarse como mínimo en una representación canónica suficientemente estable del contenido.

### RB-7
Si todas las variantes relevantes devuelven contenido equivalente, no debe emitirse señal de anti-camuflaje.

### RB-8
Si una variante devuelve contenido claramente benigno y otra devuelve contenido claramente orientado a login, phishing o cebo de credenciales, esto debe considerarse candidato fuerte a señal.

---

## 6. Flujo principal

1. El pipeline llega a la fase de análisis HTML/contenido.
2. El sistema ejecuta múltiples fetches del mismo target con distintos User-Agent.
3. El sistema normaliza/canoniza los HTML recibidos.
4. El sistema compara las variantes.
5. Si la variación supera el umbral definido:
   - emite una señal oficial de anti-camuflaje
6. Si no supera el umbral:
   - no emite señal
7. Si alguna variante falla:
   - registra warning no contractual si aplica
   - continúa mientras pueda producirse resultado mínimo contractual

---

## 7. Contratos técnicos

### 7.1 User-Agents mínimos

El sistema debe usar al menos 3 perfiles:

- desktop
- mobile
- googlebot-like

La implementación concreta de strings puede definirse en código, pero debe quedar centralizada y no dispersa.

### 7.2 Comparación mínima

La comparación debe usar al menos:

- longitud del contenido normalizado
- hash del contenido normalizado
- comparación estructural o textual suficientemente estable

### 7.3 Señal nueva

Nueva señal candidata:

- `signal_type`: `content_variation_detected`

Categoría sugerida:

- `CONTENT_BEHAVIOR`

Severidad sugerida:

- `HIGH` cuando la divergencia sea fuerte
- `MEDIUM` si la divergencia es relevante pero menos concluyente

### 7.4 Campos mínimos de la señal

La señal emitida debe incluir como mínimo:

- `signal_type`
- `category`
- `severity`
- `confidence`
- `detected`
- `title`
- `description`
- `source`

Campos deseables:

- `evidence`
- `message_key`
- `message_params`

### 7.5 Warnings

Si una o más variantes fallan, puede emitirse warning no durable, por ejemplo:

- `multi_user_agent_fetch_partially_unavailable`

Pero esta feature no convierte warnings en durables.

---

## 8. Heurística mínima de divergencia

La spec no exige un algoritmo perfecto, pero sí exige una heurística explícita y testeable.

Versión mínima aceptable:

- normalizar HTML
- eliminar ruido obvio
- comparar hash/longitud/contenido base
- detectar divergencia alta entre variantes

Casos candidatos a divergencia fuerte:

- una variante contiene formulario/login y otra no
- una variante contiene brand/phishing lure y otra no
- una variante devuelve contenido sustancialmente vacío y otra contenido completo
- diferencias masivas de estructura o texto

---

## 9. Estados y errores

### 9.1 Caso correcto
Todas las variantes se consultan y comparan correctamente.

### 9.2 Caso degradado
Una o más variantes fallan, pero se mantiene resultado contractual mínimo.

### 9.3 Caso fallido
Solo si la verificación completa no puede emitir resultado contractual mínimo por causas más amplias del pipeline.

---

## 10. Riesgos

- falsos positivos por diferencias triviales
- aumentar latencia del pipeline
- duplicar coste de fetch HTML
- mezclar demasiado esta lógica con el analizador HTML existente
- introducir mucha complejidad para una primera versión

---

## 11. Supuestos

- la infraestructura actual puede soportar 2–3 fetches por verificación en esta fase
- no se usará navegador headless en esta iteración
- una primera heurística basada en HTML normalizado es suficiente para una V1
- el contrato actual de verificación ya permite añadir nuevas señales sin romper compatibilidad

---

## 12. Criterios de aceptación

### AC-1
El sistema realiza múltiples fetches con distintos User-Agent para el análisis de contenido.

### AC-2
Si las variantes son semánticamente equivalentes, no se emite señal de anti-camuflaje.

### AC-3
Si existe divergencia significativa entre variantes, se emite una señal oficial `content_variation_detected`.

### AC-4
La verificación sigue devolviendo resultado contractual válido aunque una variante falle, siempre que el resto del pipeline pueda completarse.

### AC-5
La nueva lógica no rompe el contrato actual de verificación.

### AC-6
La implementación mantiene cambios mínimos y no introduce refactors amplios fuera de alcance.

---

## 13. Casos de test

### T-1
Desktop, mobile y googlebot devuelven HTML equivalente → no hay señal.

### T-2
Desktop devuelve formulario de login y googlebot devuelve página neutra → se emite `content_variation_detected`.

### T-3
Mobile devuelve contenido sustancialmente distinto del desktop → se emite señal si supera umbral.

### T-4
Una variante falla pero otras responden → la verificación sigue y no rompe contrato.

### T-5
Diferencias menores/noise-only no disparan señal.

### T-6
La nueva señal aparece correctamente mapeada en el resultado API.

---

## 14. Plan de implementación esperado

### Paso 1
Auditar el fetch HTML actual y decidir el punto exacto de integración.

### Paso 2
Introducir perfiles centralizados de User-Agent.

### Paso 3
Añadir fetch multi-variant con salida estructurada.

### Paso 4
Añadir normalización/canonización de HTML para comparación.

### Paso 5
Implementar heurística mínima de divergencia.

### Paso 6
Emitir señal oficial si aplica.

### Paso 7
Añadir tests unitarios e integración relevantes.

### Paso 8
Validar que no se rompe el contrato existente.

---

## 15. Decisión de esta spec

Esta feature busca una V1 pragmática de anti-evasión basada en múltiples User-Agent y comparación de HTML.

No intenta resolver todavía evasión avanzada con JavaScript, rendering headless o análisis visual.