# outbound-fetch-guard: hallazgos del baseline de OpenSpec

Informe que acompaña a `openspec/specs/outbound-fetch-guard/spec.md`, extraído de
`main@d3f9dfb`. **No se cambió código.** Cada punto cita su evidencia en el código. Los
riesgos se marcan **CONFIRMADO** (leí el código y no hay defensa) o **A VERIFICAR**. Las
pruebas empíricas se hicieron solo con la librería estándar de Python 3.11.9 en local
(`ipaddress`, `urlsplit`, `urllib.request.Request`), sin peticiones de red a destinos.

---

## 1. Reglas implícitas

Comportamiento que el código aplica sin que esté documentado en ningún sitio.

1. **Todo o nada sobre las respuestas DNS.** Si *cualquier* dirección resuelta no es global,
   se bloquea el destino entero, aunque otras respuestas sean públicas
   (`outbound_target_guard.py:resolve_safe_outbound_host`, bucle sobre `addresses`).
2. **"Privado" lo define `ipaddress.is_global` de Python.** No hay lista propia de rangos.
   Lo bloqueado depende de las tablas de la versión de Python en ejecución (ver Riesgos 4 y 5).
3. **No hay restricción de puertos.** Se acepta cualquier puerto TCP explícito. El puerto
   `0` se trata como ausente y se usa el puerto por defecto del esquema (`parsed.port or ...`,
   línea 39).
4. **Un host sin puerto se valida en el puerto 443** (`resolve_safe_outbound_host`,
   `port or 443`). Los llamadores actuales (TLS, infraestructura) pasan el puerto de forma
   explícita, así que este valor por defecto no se usa en el flujo normal.
5. **Los nombres de una sola etiqueta se bloquean** salvo que sean IP literales. Por eso la
   forma decimal sin puntos (`2130706433`) se rechaza antes de resolver DNS.
6. **El guardia se aplica a la entrada aunque el fast path vaya a saltarse la red.** Un
   dominio que no resuelve (NXDOMAIN) devuelve 422 en lugar de un veredicto
   (`create_url_verification.py:execute` → `_assert_public_target`, antes del fast path).
7. **Una verificación hace varias resoluciones DNS independientes:** entrada, redirecciones
   (dos por salto: `send_pinned_get_request` y la revalidación explícita), HTML por cada
   variante de user-agent, HTML del destino resuelto, TLS e infraestructura. Cada conexión
   se fija a *su propia* resolución validada, así que etapas distintas pueden ver IPs
   distintas.
8. **Un salto de redirección bloqueado descarta la cadena entera.** Se pierden los saltos
   ya recogidos y solo queda `warning.redirect_resolution_unavailable`
   (`http_redirect_resolver.py:resolve` → `redirect_signal_analyzer.py`). Una URL de phishing
   que redirige a una IP interna se ve como "cobertura degradada", no como señal.
9. **Los timeouts son por operación de socket, no un tope total.** Con N IPs validadas, el
   peor caso es N × timeout por petición; el resolvedor de redirecciones puede encadenar
   5 saltos. Un servidor que envía la respuesta gota a gota puede alargar la lectura, que
   solo está acotada por `max_bytes`.
10. **Límites heredados de `http.client`** (número de cabeceras y longitud de línea) protegen
    la lectura de cabeceras. No están en el código propio.
11. **El webhook se valida una vez por notificación.** Los reintentos reutilizan esa
    validación. Al enviar el scan solo se comprueba el esquema (`scan_schema.py:_validate_webhook_url`),
    y la URL se guarda sin pasar por el guardia.
12. **El log de un webhook bloqueado no incluye la URL**, solo el id del scan
    (`http_scan_webhook_notifier.py:56-58`).
13. **Los errores del guardia son claves i18n localizadas (EN/ES).** Un fallo de DNS se
    presenta como "no se pudo resolver para la validación de seguridad", no como error de red.
14. **En la práctica no se admiten IP literales IPv6 como objetivo.** `NormalizedUrl` quita
    los corchetes al reconstruir la URL (`normalized_url.py:_build_normalized_url`,
    `netloc = ascii_host`). Por ejemplo, `http://[2001:db8::1]/` pasa a `http://2001:db8::1/`.
    Después, `urlsplit` en el guardia devuelve un hostname truncado o `None`: las IPv6 que
    empiezan por `::` se rechazan como "host requerido", y el resto lanza `ValueError` en
    `parsed.port` (línea 39). Ese error no se captura en `_assert_public_target`.
    Comprobado en local llamando a `NormalizedUrl.from_raw` + `urlsplit`. Falla de forma
    cerrada (no es un bypass), pero es probable que acabe en un 500.

## 2. Huecos de tests

Escenarios de la spec con `Test: NONE` (18):

| # | Requisito | Escenario |
|---|-----------|-----------|
| 1 | Only HTTP and HTTPS | Non-HTTP scheme is rejected |
| 2 | Only HTTP and HTTPS | URL without a hostname is rejected |
| 3 | Hostnames normalized | Trailing dot and uppercase do not evade the hostname rules |
| 4 | Hostnames normalized | Empty hostname is rejected |
| 5 | Local/special-use hostnames | Special-use suffixes (`.internal`, `.local`, `.localhost`, `.home.arpa`) |
| 6 | Single-label | Dotless decimal IPv4 form is rejected as single-label |
| 7 | Globally routable | Cloud metadata link-local address (`169.254.169.254`) |
| 8 | Globally routable | Mixed public and private answers |
| 9 | Globally routable | Non-global IPv6 (`::1`, ULA, IPv4-mapped) |
| 10 | Globally routable | Non-canonical IPv4 forms judged by resolved address |
| 11 | Port defaults | http URL without a port uses port 80 |
| 12 | Port defaults | Bare host without a port uses port 443 |
| 13 | Pinned connections | Next validated address is tried after a network failure |
| 14 | Redirects | Redirect chain longer than the hop limit fails |
| 15 | Redirects | Redirect without Location fails |
| 16 | Timeouts/size | HTML body is truncated to the byte limit |
| 17 | Coverage warnings | Blocked resolved-destination fetch is identified as a private-target block |
| 18 | Coverage warnings | Blocked TLS or infrastructure lookup becomes a generic coverage warning |

Observaciones sobre los tests que sí existen:

- Los tests de integración (`test_verifications_api.py`, `test_scans_api.py`,
  `test_auth_ownership_api.py`) **sustituyen el guardia por un stub** con
  `monkeypatch.setattr(container, "assert_safe_outbound_url", ...)`. Prueban el mapeo a 422,
  no el guardia real.
- Hay tres escenarios cuyo test cubre el camino genérico (cualquier error del adaptador),
  pero no el caso concreto en que el error lo origina el guardia: el aviso de redirección,
  el fallo del job de scan y la entrada 422.
- **Ningún test cubre el poster real del webhook** (`build_urllib_webhook_poster`): ni
  redirecciones ni re-resolución DNS (ver Riesgos 1 y 2).
- `test_pinned_http_client_uses_validated_ip_for_actual_connection` pasa `max_bytes=32`,
  pero el cuerpo falso es más corto, así que no comprueba el truncado.

## 3. Discrepancias

1. **El docstring del webhook promete más de lo que el código cumple.**
   `http_scan_webhook_notifier.py:31-33` dice "a webhook can never be used to reach private
   or special-use addresses (SSRF)". Sin embargo, el envío usa `urlopen`, que sigue
   redirecciones y vuelve a resolver DNS sin pasar por el guardia (Riesgos 1 y 2).
2. **CLAUDE.md exige capas estrictas, pero la aplicación importa de infraestructura.**
   `api/app/application/use_cases/create_url_verification.py:54` importa
   `UnsafeOutboundTargetError` desde `app.infrastructure.external_services.outbound_target_guard`.
3. **Versión de Python.** CLAUDE.md dice "Backend Python here is 3.11", pero
   `api/.python-version` dice `3.12`. Como el guardia depende de `ipaddress.is_global`, cuyas
   tablas cambian entre versiones, la cobertura real depende de cuál se use en producción.
4. **`docs/PHASE-B-HEADLESS-DETONATION.md` §4** dice "the isolation boundary (not just our
   existing SSRF guard) must prevent that", lo que sugiere que el guardia participa en la
   detonación. En el código, el guardia solo valida la URL inicial (en la entrada del caso
   de uso). La navegación dentro del navegador (redirecciones, JS, subrecursos) no pasa por él.
5. **`docs/API.md`** ("private, loopback, and special-use addresses are rejected") describe
   bien el caso de entrada. No menciona que las IP literales IPv6 públicas tampoco funcionan
   (Regla implícita 14), ni explica que el webhook solo se valida al entregarse.
6. **El nombre de un test sugiere más de lo que prueba.**
   `test_outbound_target_guard_blocks_resolution_to_private_address` usa el host
   `rebind.example`, pero solo prueba la resolución directa a una IP privada, no el
   rebinding (cambio entre validar y conectar). Esa defensa la cubre el test de pinning.

## 4. Riesgos de bypass sospechados

### Vectores revisados y cubiertos (para contexto)

- **DNS rebinding en el camino del objetivo (HTML, redirecciones, TLS, infraestructura): cubierto.**
  Las conexiones se fijan a las IPs validadas (`pinned_http_client.py:_Pinned*Connection.connect`,
  `tls_client.py:29-33`), y la consulta de infraestructura no vuelve a resolver.
- **Redirecciones en el camino del objetivo: cubierto.** El cliente fijado no sigue
  redirecciones solo, y `HttpRedirectResolver` valida cada `Location` (`http_redirect_resolver.py:43-47`).
- **Formas alternativas de IPv4** (hex, octal, abreviadas): se valida la IP que devuelve
  `getaddrinfo`, que es la misma a la que se conecta, así que la forma textual no importa.
  La forma decimal sin puntos se bloquea por la regla de una sola etiqueta.
- **IPv4-mapped (`::ffff:a.b.c.d`) con IPv4 privada:** `is_global` devuelve `False` en 3.11.9 → bloqueada.
- **Parser distinto entre validación y fetch en el camino del objetivo:** el guardia y el
  cliente fijado usan el mismo `urlsplit` sobre la misma cadena.

### Riesgos

**1. CONFIRMADO: las redirecciones del webhook no se revalidan.**
Evidencia: `http_scan_webhook_notifier.py:133-147`. `build_urllib_webhook_poster` usa
`urlopen` con el opener por defecto, que incluye `HTTPRedirectHandler`. En la librería
estándar (`HTTPRedirectHandler.redirect_request`), un POST que recibe 301/302/303 se
convierte en GET a la nueva `Location` y conserva las cabeceras salvo `Content-Type` y
`Content-Length`, incluidas `X-Verifiko-*` y la firma. El guardia solo se ejecutó sobre la
URL original (`notify`, línea 54). El resultado es un SSRF ciego: solo se registra el código
de estado. Ningún test cubre el poster real.

**2. CONFIRMADO: el webhook es vulnerable a DNS rebinding (la IP cambia entre validar y conectar).**
Evidencia: `notify` valida en la línea 54 (el guardia resuelve DNS), y después
`self.http_poster(...)` (línea 67) → `urlopen`, que vuelve a resolver el nombre por su
cuenta. Cada reintento resuelve otra vez. No se fija la IP como en `pinned_http_client`.
Un dominio con TTL bajo puede pasar la validación con una IP pública y conectar a una privada.

**3. A VERIFICAR: el guardia y `urllib` parsean distinto la URL del webhook.**
Evidencia: el guardia usa `urlsplit(url).hostname`. `urllib.request.Request` usa su propio
partido de host y aplica `unquote` al host. En local divergen con userinfo
(`user@host` → urllib conserva `user@host`), con barra invertida y con `%40`. No encontré
una entrada que el guardia acepte y que `urllib` conecte a una dirección privada (las que
probé acaban en un host que no resuelve), pero la búsqueda no fue exhaustiva. El arreglo
natural del Riesgo 1 (usar el cliente fijado) también eliminaría esta diferencia.

**4. A VERIFICAR: IPv6 de transición que Python 3.11 considera globales.**
Evidencia: guardia, línea 62 (`is_global`). En 3.11.9, `64:ff9b::7f00:1` (NAT64 de
`127.0.0.1`), `2002:7f00:1::` (6to4) y `::127.0.0.1` (IPv4-compatible, obsoleta) dan
`is_global == True`. Un registro AAAA controlado por un atacante podría apuntar ahí. Que sea
explotable depende de que la red de ejecución tenga pasarela NAT64/6to4 o enrute esas
direcciones. Sin verificar en Vercel.

**5. A VERIFICAR: la cobertura depende de la versión de Python en producción.**
Evidencia: Discrepancia 3. Las tablas de `ipaddress` cambiaron en parches recientes
(por ejemplo, el tratamiento de las IPv4-mapped y nuevos rangos reservados). Hay que
confirmar qué versión ejecuta el runtime de Vercel y repetir las pruebas del Riesgo 4 con ella.

**6. A VERIFICAR: la navegación durante la detonación headless no pasa por el guardia.**
Evidencia: `browserless_detonation_client.py:51` (`page.goto(url)` dentro del script
remoto). Solo la URL inicial se valida en `_assert_public_target`. Las redirecciones, la
navegación por JS y los subrecursos no los controla nuestro código. Además, Chrome usa el
parser WHATWG (que trata `\` como `/`) en lugar de `urlsplit`. Hoy esto ocurre en la red del
proveedor gestionado, no en la nuestra. Pasa a ser un vector SSRF real si se ejecuta la ruta
de self-hosting prevista en CLAUDE.md sin aislamiento de red (lo exige
`PHASE-B-HEADLESS-DETONATION.md` §4).

**7. A VERIFICAR: llamadores que no pasan por el guardia.**
Evidencia: `urlopen` en `rdap_domain_age_lookup.py:22`, `urlhaus_reputation_client.py:33`,
`openphish_reputation_client.py:103`, `browserless_detonation_client.py:201`,
`resend_email_sender.py:64`, `google_tokeninfo_identity_verifier.py:67` y
`scan_dispatchers.py:124`. En todos el host lo fija el código o la configuración. El único
con un componente que viene del usuario es RDAP: `f"{base_url}{domain}"`, donde el dominio
sale del hostname ya normalizado, así que solo afecta a la ruta y no al host. Todos siguen
redirecciones por defecto de `urllib`, así que un upstream comprometido podría redirigir.
El riesgo es bajo, pero no hay ninguna defensa explícita.
