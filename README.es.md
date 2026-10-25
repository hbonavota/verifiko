[English](README.md) · **Español**

# Verifiko

**¿Este enlace es seguro?** Verifiko detecta enlaces de phishing y malware. Pegas una URL y en
segundos obtienes un veredicto explicable. El mismo motor está disponible para desarrolladores a
través de una API REST versionada. Está pensado como alternativa directa a herramientas como URLert.

[![Licencia: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![CI](https://github.com/hbonavota/verifiko/actions/workflows/ci.yml/badge.svg)](https://github.com/hbonavota/verifiko/actions/workflows/ci.yml)

**En producción:** https://www.verifiko.es · **API:** `https://api.verifiko.es/api/v1` ([referencia](docs/API.md))

| Landing | Veredicto |
|---|---|
| ![Landing de Verifiko: "Know if a link is safe before you click"](screenshots/landing.png) | ![Resultado de la verificación de una URL que imita a PayPal (typosquat): trust score 34, veredicto Malicious](screenshots/verification-result.png) |

## Qué hace

Cada verificación produce una **puntuación de confianza** (trust score, 0–100), un **nivel de
riesgo** (`SAFE` → `CRITICAL`) y la lista de señales que llevaron a él. Cada señal tiene una
severidad, un nivel de confianza y una explicación en inglés y español, así que el veredicto se
puede auditar en lugar de aceptarse a ciegas.

**Motor de detección**
- **Heurísticas deterministas** sobre unos 30 tipos de señal. En la URL: hosts que son una dirección
  IP, homógrafos Unicode, caracteres de ancho cero, subdominios que suplantan marcas, dominios de alta
  entropía, TLDs de riesgo y acortadores. En la página y el transporte: formularios de robo de
  credenciales, señuelos con aspecto de pantalla de login, fallos de TLS y discrepancias de hostname,
  cadenas de redirección sospechosas y antigüedad del registro del dominio (RDAP).
- **Typosquatting de marcas** (`paypa1.com`, `g00gle.com`), detectado mediante normalización de
  leetspeak más distancia de edición.
- **Agregación de reputación** entre URLhaus y OpenPhish. Una regla de **consenso 2-de-N** evita que
  un solo feed ruidoso decida el veredicto, y cada proveedor está detrás de un **circuit breaker**.
- **Política de scoring ponderada** más **reglas compuestas**, que escalan combinaciones de señales y
  señales decisivas por sí solas.
- **Orquestación por oleadas**: los analizadores que dependen de la red corren en oleadas ordenadas
  por dependencia, y las consultas de reputación, antigüedad del dominio e infraestructura se cachean
  en Redis. Un camino **fail-fast** se salta las oleadas de red cuando la URL por sí sola ya es
  `HIGH`/`CRITICAL`.

**Producto y API**
- App web pública: verificaciones anónimas con cuota diaria. Las cuentas inician sesión con
  **Google**, un **magic link por email** o email + contraseña.
- **API keys** para desarrolladores y la superficie versionada **`/api/v1`**, con cuotas diarias por
  plan y límites de ráfaga.
- **Pipeline de escaneo asíncrono**: `POST /scans` (o `/scans/batch`) → `202`, y después se consulta
  `GET /scans/{id}` o se recibe un **webhook** firmado. Los jobs viven en Postgres. El despacho corre
  en el mismo proceso o a través de una cola (Upstash QStash) para runtimes serverless.
- **Análisis profundo** (deep scan; usuarios con sesión iniciada, solo asíncrono, detrás de un
  feature flag): la URL se detona en un navegador headless (Browserless). Las señales de
  comportamiento entran al scoring antes del veredicto: un formulario de credenciales renderizado, un
  formulario que envía a otro dominio, una redirección por JS a otro dominio, una descarga automática
  (drive-by). Se guarda una captura en Cloudflare R2, que se sirve mediante una URL prefirmada de
  corta duración.
- Inglés y español en todo: interfaz, veredictos y mensajes de error de la API.

**Roadmap (todavía no construido)**
- Calibrar los pesos de detección contra un corpus específico de detonación.
- Visión artificial sobre las capturas del análisis profundo: reconocimiento de logos de marca y
  detección visual de logins falsos.
- Facturación por uso (créditos), un producto de clasificación de dominios, un threat feed público y
  una extensión de navegador.

## Arquitectura

```text
   Navegador (SPA React)            Clientes de la API (X-API-Key)
   www.verifiko.es                           │
          └───────────────┬──────────────────┘
                          ▼
             FastAPI  ·  /api/v1  ·  api.verifiko.es
  ┌──────────────────────────────────────────────────────────┐
  │ entrypoints     rutas, schemas, contenedor DI            │
  │ application     casos de uso, analizadores, puertos      │
  │ domain          entidades, scoring, reglas compuestas    │
  │ infrastructure  adaptadores detrás de los puertos ↓      │
  └──────────────────────────────────────────────────────────┘
   Postgres (Neon)   Redis (Upstash)   URLhaus · OpenPhish · RDAP
   SQLAlchemy +      limiters, cachés  fetchers HTML / TLS / DNS
   Alembic                             (con guard SSRF, IP fijada)
   Browserless · Cloudflare R2 · Resend · QStash   (opcionales)
```

- **Backend** (`api/`): Python 3.11, FastAPI y **Clean Architecture** con capas estrictas. El
  dominio no hace I/O. El código de aplicación depende solo de puertos. Los adaptadores de
  infraestructura se registran en un único contenedor de inyección de dependencias
  (`app/entrypoints/api/dependencies/container.py`). A Postgres se accede con SQLAlchemy y
  psycopg v3, con migraciones de Alembic.
- **Frontend** (`web/`): React 18, TypeScript y Vite, con React Router e i18n en inglés y español.
  La landing se renderiza en el servidor durante el build (prerenderizada). El soporte de PWA
  (service worker + aviso de instalación) está detrás de un flag de build.
- **Deploy**: dos proyectos de Vercel, la API (`api/index.py`) y el frontend estático. Las
  migraciones del esquema corren desde una GitHub Action cada vez que llega una migración a `main`,
  por separado del deploy del código (ver [`api/DEPLOY.md`](api/DEPLOY.md)).

Las capacidades de riesgo se publican **detrás de feature flags desactivados por defecto**: análisis
profundo, almacenamiento de capturas, el camino fail-fast, el feed de OpenPhish y el despacho por cola.
Así, cada capacidad nueva llega apagada hasta que se habilita de forma explícita.

## Destacados de seguridad

- **Guard contra SSRF en cada request saliente a destinos controlados por el usuario**: objetivos de
  verificación, redirecciones, consultas HTML/TLS/DNS y URLs de webhooks. El guard solo permite
  `http`/`https`, rechaza hostnames internos, resuelve el DNS y bloquea la request salvo que **todas**
  las direcciones resueltas sean enrutables globalmente. Eso incluye direcciones IPv4 embebidas en
  IPv6: IPv4-mapped, 6to4, Teredo, NAT64 e IPv4-compatible. Después, los adaptadores se conectan solo
  a la **IP validada y fijada**, lo que cierra los bypass por DNS rebinding/TOCTOU y por seguimiento
  de redirecciones.
- **Falla de forma segura en producción**: la API se niega a arrancar si un secreto de firma no está
  definido, está vacío o sigue con su valor por defecto de desarrollo.
- **Webhooks firmados**: HMAC-SHA256 sobre `timestamp.body`, enviado como `X-Verifiko-Signature`. Ver
  [cómo verificarlo](docs/API.md#verifying-the-signature).
- **Worker interno autenticado**: los callbacks de la cola deben traer un JWT de QStash válido
  (HS256, con rotación de clave actual/siguiente).
- **Credenciales en reposo**: las contraseñas se hashean con Argon2. Las API keys se guardan solo
  como hashes SHA-256 y se muestran una única vez.
- **IP del cliente para las cuotas**: se toma de `X-Forwarded-For` solo cuando la request llega desde
  un proxy de confianza configurado.

## Ejecutarlo en local

Requisitos: Python 3.11, Node.js 18+ y Docker (para el Postgres local).

**API**

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # valores por defecto para desarrollo; cada variable está documentada
docker compose up -d db
alembic upgrade head
uvicorn app.entrypoints.api.main:app --reload --port 8000
```

`api/.env.example` lista cada setting por nombre. Sin configuración extra se obtiene una API local
funcionando solo con Postgres. Redis, Google Sign-In (`GOOGLE_CLIENT_ID`), email
(`RESEND_API_KEY`), deep scan (`DETONATION_ENABLED`, `BROWSERLESS_ENDPOINT`) y el almacenamiento de
capturas (`SCREENSHOT_STORAGE_ENABLED`, `R2_*`) son opcionales. En producción, `AUTH_TOKEN_SECRET` y
`SCAN_WEBHOOK_SIGNING_SECRET` son obligatorios.

**Web**

```bash
cd web
npm ci
npm run dev                   # http://localhost:5173, habla con http://localhost:8000
```

En desarrollo, la app apunta a `http://localhost:8000` cuando `VITE_API_BASE_URL` no está definida.
Copia `web/.env.example` a `.env` solo si necesitas definir `VITE_GOOGLE_CLIENT_ID`, y en ese caso
define también `VITE_API_BASE_URL=http://localhost:8000`.

## Testing

```bash
cd api
python -m pytest -q                      # ~500 tests unitarios y de integración
python -m evaluation.run_evaluation      # harness de calidad de detección
```

El harness de evaluación puntúa el motor offline contra un corpus etiquetado de URLs maliciosas y
benignas. Con el umbral `MEDIUM`, la línea base actual es **precision 1.00, recall 0.82, tasa de
falsos positivos 0.00**. Los cambios no pueden empeorar la precision.

Frontend:

```bash
cd web
npm run test                             # Vitest + Testing Library (jsdom)
npm run build                            # chequeo de tipos (tsc --noEmit), build y prerender
```

Los tests unitarios viven junto al código que cubren (`src/**/*.test.{ts,tsx}`). El CI corre lint,
tests y build de la API y de la app web en cada pull request (ver el badge de arriba), con el
harness de evaluación de detección como gate contra regresiones.

Además, la app web se prueba a mano en un navegador real antes y después de cada cambio, en
distintos viewports, en ambos idiomas y como PWA. El proceso está descrito en
[docs/QA.md](docs/QA.md).

## Cambios guiados por specs

Los cambios de comportamiento pasan por [OpenSpec](https://github.com/Fission-AI/OpenSpec). Cada uno
empieza como una propuesta con un delta de spec, diseño y tareas en `openspec/changes/`, y una vez
integrado se archiva en las specs vivas de cada capacidad, en [`openspec/specs/`](openspec/specs/).
Algunos ejemplos son el guard de requests salientes y las reglas de seguridad de la configuración de
producción. Los refactors puros, la documentación y el mantenimiento de dependencias no pasan por
OpenSpec.

## Estructura del repositorio

```text
api/          Servicio FastAPI (app/{domain,application,infrastructure,entrypoints}), tests, evaluation
web/          App React + Vite + TypeScript
docs/         Referencia de la API y docs de diseño (detonación headless, capturas en R2, PWA)
openspec/     Specs de capacidades y propuestas de cambio archivadas
screenshots/  Imágenes usadas en este README
```

## Licencia

[Apache License 2.0](LICENSE) © 2026 Hernán Bonavota
