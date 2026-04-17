MESSAGES: dict[str, dict[str, str | dict[str, str]]] = {
    "signal.direct_ip_address_target": {
        "en": {
            "title": "Direct IP address target",
            "description": "The input targets an IP address directly instead of a named host.",
        },
        "es": {
            "title": "Destino directo por dirección IP",
            "description": "La entrada apunta directamente a una dirección IP en lugar de a un host con nombre.",
        },
    },
    "signal.unicode_or_punycode_hostname_pattern": {
        "en": {
            "title": "Unicode or punycode hostname pattern",
            "description": "The hostname contains unicode characters or punycode labels that merit homograph review.",
        },
        "es": {
            "title": "Patrón de hostname con Unicode o punycode",
            "description": "El hostname contiene caracteres Unicode o etiquetas punycode que requieren revisión de homógrafos.",
        },
    },
    "signal.invisible_hostname_characters": {
        "en": {
            "title": "Invisible hostname characters",
            "description": "Zero-width characters were found in the hostname representation.",
        },
        "es": {
            "title": "Caracteres invisibles en el hostname",
            "description": "Se encontraron caracteres de ancho cero en la representación del hostname.",
        },
    },
    "signal.non_standard_port_usage": {
        "en": {
            "title": "Non-standard port usage",
            "description": "The URL uses a non-standard web port, which increases handling risk.",
        },
        "es": {
            "title": "Uso de puerto no estándar",
            "description": "La URL utiliza un puerto web no estándar, lo que aumenta el riesgo de manejo.",
        },
    },
    "signal.shortened_destination": {
        "en": {
            "title": "Shortened destination",
            "description": "The URL uses a known shortening service that obscures the eventual destination.",
        },
        "es": {
            "title": "Destino acortado",
            "description": "La URL utiliza un servicio de acortamiento conocido que oculta el destino final.",
        },
    },
    "signal.redirect_style_parameters": {
        "en": {
            "title": "Redirect-style parameters",
            "description": "The URL contains redirect-style routing hints that can conceal the final destination.",
        },
        "es": {
            "title": "Parámetros con patrón de redirección",
            "description": "La URL contiene indicios de redirección que pueden ocultar el destino final.",
        },
    },
    "signal.credential_lure_wording_in_url": {
        "en": {
            "title": "Credential-lure wording in URL",
            "description": "The host or path contains account and verification language commonly used in phishing lures.",
        },
        "es": {
            "title": "Cebo de credenciales en la URL",
            "description": "El host o la ruta contienen lenguaje de cuenta y verificación usado habitualmente en cebos de phishing.",
        },
    },
    "signal.brand_like_impersonation_hints": {
        "en": {
            "title": "Brand-like impersonation hints",
            "description": "Brand references are combined with account-action language in a non-official domain.",
        },
        "es": {
            "title": "Indicios de suplantación de marca",
            "description": "Las referencias de marca se combinan con lenguaje de acción sobre la cuenta en un dominio no oficial.",
        },
    },
    "signal.institution_style_payment_or_penalty_lure": {
        "en": {
            "title": "Institution-style payment or penalty lure",
            "description": "Government or authority-style payment, traffic, or penalty wording appears on a non-official domain.",
        },
        "es": {
            "title": "Cebo institucional de pago o sanción",
            "description": "Aparece lenguaje de pago, tráfico o sanciones con apariencia gubernamental o institucional en un dominio no oficial.",
        },
    },
    "signal.mailbox_access_lure_pattern": {
        "en": {
            "title": "Mailbox access lure pattern",
            "description": "The URL combines mailbox-style terms with account-action cues.",
        },
        "es": {
            "title": "Patrón de cebo de acceso al correo",
            "description": "La URL combina términos de buzón de correo con indicios de acciones sobre la cuenta.",
        },
    },
    "signal.deceptive_brand_in_subdomain_pattern": {
        "en": {
            "title": "Deceptive brand-in-subdomain pattern",
            "description": "The subdomain embeds a brand-like domain fragment before the actual registered domain.",
        },
        "es": {
            "title": "Patrón engañoso de marca en subdominio",
            "description": "El subdominio incrusta un fragmento con apariencia de marca antes del dominio registrado real.",
        },
    },
    "signal.misleading_subdomain_structure": {
        "en": {
            "title": "Misleading subdomain structure",
            "description": "The subdomain structure adds unusual depth or trust-signaling lure wording ahead of the registered domain.",
        },
        "es": {
            "title": "Estructura de subdominio engañosa",
            "description": "La estructura del subdominio añade una profundidad inusual o lenguaje de señuelo que transmite confianza antes del dominio registrado.",
        },
    },
    "signal.high_entropy_hostname_token": {
        "en": {
            "title": "High-entropy hostname token",
            "description": "One hostname label appears algorithmically generated or unusually noisy.",
        },
        "es": {
            "title": "Token de hostname con alta entropía",
            "description": "Una etiqueta del hostname parece generada algorítmicamente o inusualmente ruidosa.",
        },
    },
    "signal.brand_like_domain_on_uncommon_tld": {
        "en": {
            "title": "Brand-like domain on uncommon TLD",
            "description": "The hostname mixes brand or account language with a higher-risk TLD choice.",
        },
        "es": {
            "title": "Dominio con apariencia de marca en un TLD inusual",
            "description": "El hostname mezcla lenguaje de marca o cuenta con un TLD de mayor riesgo.",
        },
    },
    "signal.recognized_reputable_domain": {
        "en": {
            "title": "Recognized reputable domain",
            "description": "The registered domain matches a conservative curated set of widely used reputable destinations.",
        },
        "es": {
            "title": "Dominio reputado reconocido",
            "description": "El dominio registrado coincide con un conjunto conservador y curado de destinos reputados y ampliamente utilizados.",
        },
    },
    "signal.very_recent_domain_registration": {
        "en": {
            "title": "Very recent domain registration",
            "description": "The registered domain appears to have been created within the last {threshold_days} days.",
        },
        "es": {
            "title": "Registro de dominio muy reciente",
            "description": "El dominio registrado parece haberse creado en los últimos {threshold_days} días.",
        },
    },
    "signal.recent_domain_registration": {
        "en": {
            "title": "Recent domain registration",
            "description": "The registered domain appears to have been created within the last {threshold_days} days.",
        },
        "es": {
            "title": "Registro de dominio reciente",
            "description": "El dominio registrado parece haberse creado en los últimos {threshold_days} días.",
        },
    },
    "signal.observed_redirect_chain": {
        "en": {
            "title": "Observed redirect chain",
            "description": "The submitted URL resolved through one or more redirects before reaching its final destination.",
        },
        "es": {
            "title": "Cadena de redirecciones observada",
            "description": "La URL enviada se resolvió mediante una o más redirecciones antes de alcanzar su destino final.",
        },
    },
    "signal.questionable_destination_tld_after_redirect": {
        "en": {
            "title": "Questionable destination TLD after redirect",
            "description": "The redirect chain resolves to a final destination that uses a more suspicious top-level domain.",
        },
        "es": {
            "title": "TLD de destino cuestionable tras la redirección",
            "description": "La cadena de redirección resuelve a un destino final que utiliza un dominio de nivel superior más sospechoso.",
        },
    },
    "signal.credential_capture_form_detected": {
        "en": {
            "title": "Credential capture form detected",
            "description": "The fetched HTML contains a form pattern consistent with credential collection.",
        },
        "es": {
            "title": "Formulario de captura de credenciales detectado",
            "description": "El HTML recuperado contiene un patrón de formulario coherente con la recopilación de credenciales.",
        },
    },
    "signal.suspicious_login_style_interface": {
        "en": {
            "title": "Suspicious login-style interface",
            "description": "The fetched HTML exposes login-style wording and input hints that merit credential-harvesting review.",
        },
        "es": {
            "title": "Interfaz de inicio de sesión sospechosa",
            "description": "El HTML recuperado expone lenguaje de inicio de sesión e indicios de entrada que requieren revisión por posible captura de credenciales.",
        },
    },
    "signal.parked_or_placeholder_landing_page": {
        "en": {
            "title": "Parked or placeholder landing page",
            "description": "The fetched HTML looks like a parked domain, default hosting page, or placeholder landing page.",
        },
        "es": {
            "title": "Página de aterrizaje aparcada o provisional",
            "description": "El HTML recuperado parece corresponder a un dominio aparcado, una página por defecto del hosting o una página provisional.",
        },
    },
    "signal.low_information_landing_page": {
        "en": {
            "title": "Low-information landing page",
            "description": "The fetched HTML contains almost no meaningful visible content, which limits confidence in a clean result.",
        },
        "es": {
            "title": "Página de aterrizaje con poca información",
            "description": "El HTML recuperado contiene muy poco contenido visible con significado, lo que limita la confianza en un resultado limpio.",
        },
    },
    "signal.content_variation_detected": {
        "en": {
            "title": "Content variation detected across user-agent profiles",
            "description": "The same URL served materially different normalized HTML across browser profiles, which is consistent with evasive or camouflaged delivery.",
        },
        "es": {
            "title": "Variación de contenido detectada entre perfiles de user-agent",
            "description": "La misma URL sirvió HTML normalizado materialmente distinto entre perfiles de navegador, lo que es coherente con una entrega evasiva o camuflada.",
        },
    },
    "signal.insecure_transport_scheme_plain": {
        "en": {
            "title": "Insecure transport scheme",
            "description": "The target uses plain HTTP without TLS protection.",
        },
        "es": {
            "title": "Esquema de transporte inseguro",
            "description": "El destino utiliza HTTP en claro sin protección TLS.",
        },
    },
    "signal.insecure_transport_scheme_sensitive": {
        "en": {
            "title": "Insecure transport scheme",
            "description": "The target uses plain HTTP despite exposing login-oriented or brand-sensitive cues.",
        },
        "es": {
            "title": "Esquema de transporte inseguro",
            "description": "El destino utiliza HTTP en claro a pesar de exponer indicios orientados a inicio de sesión o sensibles para la marca.",
        },
    },
    "signal.tls_validation_failure": {
        "en": {
            "title": "TLS validation failure",
            "description": "The HTTPS endpoint could not be validated with the system TLS trust store.",
        },
        "es": {
            "title": "Fallo de validación TLS",
            "description": "El endpoint HTTPS no pudo validarse con el almacén de confianza TLS del sistema.",
        },
    },
    "signal.reputation_blacklist_match": {
        "en": {
            "title": "Reputation blacklist match",
            "description": "The target or a resolved redirect destination matched external malicious URL reputation intelligence.",
        },
        "es": {
            "title": "Coincidencia en lista negra de reputación",
            "description": "El destino o un destino final resuelto por redirección coincidió con inteligencia externa de reputación maliciosa.",
        },
    },
    "signal.suspicious_infrastructure_pattern": {
        "en": {
            "title": "Suspicious infrastructure pattern",
            "description": "The effective target resolves to infrastructure with reverse-DNS patterns consistent with disposable, dynamic, or residential hosting.",
        },
        "es": {
            "title": "Patrón de infraestructura sospechoso",
            "description": "El destino efectivo resuelve a una infraestructura con patrones de DNS inverso coherentes con alojamiento desechable, dinámico o residencial.",
        },
    },
    "summary.terminal_blacklist_override": {
        "en": "Terminal override triggered by high-confidence blacklist match.",
        "es": "Se activó una invalidación terminal por una coincidencia de lista negra de alta confianza.",
    },
    "summary.risk_detected": {
        "en": "Detected {risk_signal_count} risk signal(s) with {risk_level} risk output. Category penalties totaled {category_total_penalty:.2f} and compound penalties totaled {compound_penalty:.2f}.",
        "es": "Se detectaron {risk_signal_count} señal(es) de riesgo con un resultado de riesgo {risk_level}. Las penalizaciones por categoría sumaron {category_total_penalty:.2f} y los ajustes compuestos sumaron {compound_penalty:.2f}.",
    },
    "summary.primary_concern": {
        "en": "Primary concern: {reason}. {summary}",
        "es": "Principal riesgo: {reason}. {summary}",
    },
    "summary.secondary_factors": {
        "en": "{summary} Additional risk indicators were also detected.",
        "es": "{summary} También se detectaron otros indicadores de riesgo.",
    },
    "summary.rules": {
        "en": "{summary} Compound pattern adjustments applied: {rule_count}.",
        "es": "{summary} Ajustes por patrones compuestos aplicados: {rule_count}.",
    },
    "summary.supporting_trust_context": {
        "en": "{summary} Supporting trust context: {trust_context}.",
        "es": "{summary} Contexto de confianza de apoyo: {trust_context}.",
    },
    "summary.analysis_coverage_degraded": {
        "en": "Analysis coverage degraded: {warnings} {summary}",
        "es": "Cobertura del análisis degradada: {warnings} {summary}",
    },
    "summary.reason.suspicious_redirect_chain": {
        "en": "suspicious redirection behavior",
        "es": "comportamiento sospechoso de redirección",
    },
    "summary.reason.low_information_page": {
        "en": "lack of meaningful content on the destination page",
        "es": "falta de contenido significativo en la página de destino",
    },
    "summary.reason.credential_harvest_form": {
        "en": "possible credential harvesting behavior",
        "es": "posible comportamiento de captación de credenciales",
    },
    "summary.reason.suspicious_login_interface": {
        "en": "a suspicious login-style interface",
        "es": "una interfaz sospechosa de inicio de sesión",
    },
    "summary.reason.tls_validation_failure": {
        "en": "transport security validation problems",
        "es": "problemas de validación de la seguridad del transporte",
    },
    "summary.reason.insecure_transport": {
        "en": "insecure transport without TLS protection",
        "es": "transporte inseguro sin protección TLS",
    },
    "summary.reason.brand_impersonation": {
        "en": "brand or institution impersonation cues",
        "es": "indicios de suplantación de marca o institución",
    },
    "summary.reason.suspicious_infrastructure_pattern": {
        "en": "suspicious hosting or infrastructure patterns",
        "es": "patrones sospechosos de alojamiento o infraestructura",
    },
    "summary.reason.content_variation_detected": {
        "en": "materially different content across user-agent profiles",
        "es": "contenido materialmente distinto entre perfiles de user-agent",
    },
    "explanation.headline.terminal_override": {
        "en": "The result was forced to a terminal malicious outcome by trusted backend intelligence.",
        "es": "El resultado se forzó a un desenlace malicioso terminal mediante inteligencia de backend de alta confianza.",
    },
    "explanation.headline.no_high_confidence": {
        "en": "The engine produced a {verdict} outcome without high-confidence driver signals.",
        "es": "El motor produjo un resultado {verdict} sin señales impulsoras de alta confianza.",
    },
    "explanation.headline.safe_with_trust_context": {
        "en": "The engine produced a {verdict} outcome supported by {drivers}.",
        "es": "El motor produjo un resultado {verdict} respaldado por {drivers}.",
    },
    "explanation.headline.primary_concern": {
        "en": "The engine produced a {verdict} outcome. Primary concern: {reason}.",
        "es": "El motor produjo un resultado {verdict}. Principal riesgo: {reason}.",
    },
    "explanation.headline.driven_by": {
        "en": "The engine produced a {verdict} outcome driven by {drivers}.",
        "es": "El motor produjo un resultado {verdict} impulsado por {drivers}.",
    },
    "explanation.decision_basis.with_trust_context": {
        "en": "Score {score} mapped to {risk_level} risk with {category_summary}. Supporting trust context: {drivers}.",
        "es": "La puntuación {score} se asignó al nivel de riesgo {risk_level} con {category_summary}. Contexto de confianza de apoyo: {drivers}.",
    },
    "explanation.decision_basis.primary_reason": {
        "en": "This result is mainly driven by {reason}. Score {score} mapped to {risk_level} risk. Main contributing categories: {category_summary}.",
        "es": "Este resultado está impulsado principalmente por {reason}. La puntuación {score} se asignó al nivel de riesgo {risk_level}. Principales categorías contribuyentes: {category_summary}.",
    },
    "explanation.decision_basis.no_primary_factors": {
        "en": "Score {score} mapped to {risk_level} risk with {category_summary}.",
        "es": "La puntuación {score} se asignó al nivel de riesgo {risk_level} con {category_summary}.",
    },
    "explanation.decision_basis.main_categories": {
        "en": "Score {score} mapped to {risk_level} risk. Main contributing categories: {category_summary}.",
        "es": "La puntuación {score} se asignó al nivel de riesgo {risk_level}. Principales categorías contribuyentes: {category_summary}.",
    },
    "phrase.no_category_penalties_recorded": {
        "en": "no category penalties recorded",
        "es": "sin penalizaciones por categoría registradas",
    },
    "phrase.tls_reason_certificate_verify_failed": {
        "en": "certificate verify failed",
        "es": "falló la verificación del certificado",
    },
    "phrase.tls_reason_hostname_mismatch": {
        "en": "hostname mismatch",
        "es": "discordancia del nombre de host",
    },
    "phrase.placeholder_empty_value": {
        "en": "(empty)",
        "es": "(vacío)",
    },
    "phrase.placeholder_none_value": {
        "en": "(none)",
        "es": "(ninguno)",
    },
    "phrase.infrastructure_pattern_dynamic_dns": {
        "en": "dynamic-dns",
        "es": "DNS dinámico",
    },
    "phrase.infrastructure_pattern_residential_ptr": {
        "en": "residential-ptr",
        "es": "PTR residencial",
    },
    "warning.domain_registration_unavailable": {
        "en": "Domain registration intelligence was unavailable for this run.",
        "es": "La inteligencia de registro del dominio no estuvo disponible en esta ejecución.",
    },
    "warning.redirect_resolution_unavailable": {
        "en": "Redirect resolution could not be completed for this run.",
        "es": "La resolución de redirecciones no pudo completarse en esta ejecución.",
    },
    "warning.blacklist_reputation_unavailable": {
        "en": "Blacklist reputation intelligence was unavailable for this run.",
        "es": "La inteligencia de reputación de listas negras no estuvo disponible en esta ejecución.",
    },
    "warning.infrastructure_unavailable": {
        "en": "Infrastructure intelligence could not be completed for this run.",
        "es": "La inteligencia de infraestructura no pudo completarse en esta ejecución.",
    },
    "warning.tls_validation_unavailable": {
        "en": "TLS validation could not be completed for this run.",
        "es": "La validación TLS no pudo completarse en esta ejecución.",
    },
    "warning.html_content_inspection_unavailable": {
        "en": "HTML content inspection could not be completed.",
        "es": "La inspección del contenido HTML no pudo completarse.",
    },
    "warning.resolved_destination_html_unavailable": {
        "en": "Resolved destination HTML inspection could not be completed.",
        "es": "La inspección HTML del destino resuelto no pudo completarse.",
    },
    "warning.multi_user_agent_fetch_partially_unavailable": {
        "en": "Some user-agent HTML variants could not be fetched, but the analysis continued with the variants that responded.",
        "es": "Algunas variantes HTML por user-agent no pudieron obtenerse, pero el análisis continuó con las variantes que sí respondieron.",
    },
    "warning.html_fetch_blocked_private_target": {
        "en": "HTML content fetch was blocked for a private or special-use target.",
        "es": "La obtención del contenido HTML fue bloqueada por apuntar a un destino privado o de uso especial.",
    },
    "error.client_supplied_signals_not_accepted": {
        "en": "Client-supplied signals are not accepted on this endpoint.",
        "es": "Las señales proporcionadas por el cliente no se aceptan en este endpoint.",
    },
    "error.public_verification_history_disabled": {
        "en": "Public verification history is disabled on this endpoint.",
        "es": "El historial público de verificaciones está deshabilitado en este endpoint.",
    },
    "error.public_verification_retrieval_disabled": {
        "en": "Public verification retrieval is disabled on this endpoint.",
        "es": "La recuperación pública de verificaciones está deshabilitada en este endpoint.",
    },
    "error.anonymous_daily_verification_limit_exceeded": {
        "en": "The anonymous verification limit for today has been reached. Please try again after midnight UTC or sign in.",
        "es": "Se ha alcanzado el límite anónimo de verificaciones para hoy. Vuelve a intentarlo después de la medianoche UTC o inicia sesión.",
    },
    "error.authenticated_daily_limit_exceeded": {
        "en": "You’ve reached your daily verification limit. Upgrade to continue.",
        "es": "Has alcanzado tu límite diario de verificaciones. Mejora tu plan para continuar.",
    },
    "error.verification_burst_rate_limit_exceeded": {
        "en": "Too many verification requests in a short period. Please wait a moment and try again.",
        "es": "Demasiadas solicitudes de verificación en un período corto. Espera un momento y vuelve a intentarlo.",
    },
    "error.authentication_required": {
        "en": "Authentication is required for this endpoint.",
        "es": "Se requiere autenticación para este endpoint.",
    },
    "error.invalid_authentication_token": {
        "en": "Authentication token is invalid or expired.",
        "es": "El token de autenticación no es válido o ha caducado.",
    },
    "error.google_identity_token_invalid": {
        "en": "Google identity token could not be verified.",
        "es": "No se pudo verificar el token de identidad de Google.",
    },
    "error.google_authentication_not_configured": {
        "en": "Google authentication is not configured for this environment.",
        "es": "La autenticación de Google no está configurada para este entorno.",
    },
    "error.local_auth_invalid_credentials": {
        "en": "Email or password is incorrect.",
        "es": "El correo o la contraseña son incorrectos.",
    },
    "error.email_already_registered": {
        "en": "An account already exists for this email.",
        "es": "Ya existe una cuenta para este correo.",
    },
    "error.verification_not_found": {
        "en": "Verification not found: {verification_id}",
        "es": "Verificación no encontrada: {verification_id}",
    },
    "error.invalid_verification_id": {
        "en": "Invalid verification id.",
        "es": "ID de verificación no válido.",
    },
    "error.url_input_empty": {
        "en": "URL input cannot be empty.",
        "es": "La URL de entrada no puede estar vacía.",
    },
    "error.only_http_https_urls_supported": {
        "en": "Only HTTP and HTTPS URLs are supported.",
        "es": "Solo se admiten URLs HTTP y HTTPS.",
    },
    "error.url_host_required": {
        "en": "URL host is required.",
        "es": "Se requiere un host en la URL.",
    },
    "error.invalid_unicode_host_name": {
        "en": "Invalid unicode host name.",
        "es": "Nombre de host Unicode no válido.",
    },
    "error.only_http_https_outbound_targets_allowed": {
        "en": "Only HTTP and HTTPS outbound targets are allowed.",
        "es": "Solo se permiten destinos salientes HTTP y HTTPS.",
    },
    "error.outbound_target_host_required": {
        "en": "Outbound target host is required.",
        "es": "Se requiere un host para el destino saliente.",
    },
    "error.outbound_target_local_special_use_blocked": {
        "en": "Outbound target is a local or special-use hostname and was blocked.",
        "es": "El destino saliente es un hostname local o de uso especial y fue bloqueado.",
    },
    "error.outbound_target_single_label_blocked": {
        "en": "Outbound target uses a single-label hostname and was blocked.",
        "es": "El destino saliente usa un hostname de una sola etiqueta y fue bloqueado.",
    },
    "error.outbound_target_private_special_use_address_blocked": {
        "en": "Outbound target resolved to a private or special-use address and was blocked.",
        "es": "El destino saliente resolvió a una dirección privada o de uso especial y fue bloqueado.",
    },
    "error.outbound_target_host_unresolved_for_safety_validation": {
        "en": "Outbound target host could not be resolved for safety validation.",
        "es": "El host del destino saliente no pudo resolverse para la validación de seguridad.",
    },
    "evidence.host_resolves_to_raw_ip": {
        "en": "Host resolves to raw IP {ascii_host}.",
        "es": "El host apunta directamente a la IP {ascii_host}.",
    },
    "evidence.rendered_host": {
        "en": "Rendered host: {host}.",
        "es": "Host mostrado: {host}.",
    },
    "evidence.ascii_host_contains_punycode_labels": {
        "en": "ASCII host contains punycode label(s): {ascii_host}.",
        "es": "El host ASCII contiene etiquetas punycode: {ascii_host}.",
    },
    "evidence.ascii_host": {
        "en": "ASCII host: {ascii_host}.",
        "es": "Host ASCII: {ascii_host}.",
    },
    "evidence.host_contains_zero_width_characters": {
        "en": "Host contains zero-width characters: {host}.",
        "es": "El host contiene caracteres de ancho cero: {host}.",
    },
    "evidence.observed_explicit_port": {
        "en": "Observed explicit port {port}.",
        "es": "Puerto explícito observado: {port}.",
    },
    "evidence.registered_domain_is_shortener": {
        "en": "Registered domain {registered_domain} is a shortener.",
        "es": "El dominio registrado {registered_domain} es un acortador.",
    },
    "evidence.path_contains_redirect_style_tokens": {
        "en": "Path contains redirect-style token(s): {decoded_path}.",
        "es": "La ruta contiene tokens de redirección: {decoded_path}.",
    },
    "evidence.query_parameter_may_steer_navigation": {
        "en": "Query parameter {key}={value} may steer navigation.",
        "es": "El parámetro de consulta {key}={value} puede dirigir la navegación.",
    },
    "evidence.query_parameter_embeds_nested_url": {
        "en": "Query parameter {key} embeds a nested URL destination.",
        "es": "El parámetro de consulta {key} incrusta un destino URL anidado.",
    },
    "evidence.matched_url_keywords": {
        "en": "Matched URL keywords: {keywords}.",
        "es": "Palabras clave de URL coincidentes: {keywords}.",
    },
    "evidence.matched_brand_terms": {
        "en": "Matched brand terms: {brands}.",
        "es": "Términos de marca coincidentes: {brands}.",
    },
    "evidence.registered_domain_under_review": {
        "en": "Registered domain under review: {registered_domain}.",
        "es": "Dominio registrado bajo revisión: {registered_domain}.",
    },
    "evidence.matched_institution_terms": {
        "en": "Matched institution terms: {terms}.",
        "es": "Términos institucionales coincidentes: {terms}.",
    },
    "evidence.matched_demand_terms": {
        "en": "Matched demand terms: {terms}.",
        "es": "Términos de exigencia coincidentes: {terms}.",
    },
    "evidence.matched_mailbox_terms": {
        "en": "Matched mailbox terms: {terms}.",
        "es": "Términos de buzón coincidentes: {terms}.",
    },
    "evidence.observed_deceptive_fragment": {
        "en": "Observed deceptive fragment: {fragment}.",
        "es": "Fragmento engañoso observado: {fragment}.",
    },
    "evidence.registered_domain_observed": {
        "en": "Registered domain observed: {registered_domain}.",
        "es": "Dominio registrado observado: {registered_domain}.",
    },
    "evidence.subdomain_observed": {
        "en": "Subdomain observed: {subdomain}.",
        "es": "Subdominio observado: {subdomain}.",
    },
    "evidence.matched_suspicious_subdomain_labels": {
        "en": "Matched suspicious subdomain labels: {labels}.",
        "es": "Etiquetas sospechosas de subdominio coincidentes: {labels}.",
    },
    "evidence.subdomain_label_count_observed": {
        "en": "Subdomain label count observed: {count}.",
        "es": "Cantidad de etiquetas de subdominio observada: {count}.",
    },
    "evidence.suspicious_label": {
        "en": "Suspicious label: {label}.",
        "es": "Etiqueta sospechosa: {label}.",
    },
    "evidence.matched_suspicious_hostname_terms": {
        "en": "Matched suspicious hostname terms: {terms}.",
        "es": "Términos sospechosos de hostname coincidentes: {terms}.",
    },
    "evidence.observed_tld": {
        "en": "Observed TLD: .{tld}.",
        "es": "TLD observado: .{tld}.",
    },
    "evidence.observed_domain": {
        "en": "Observed domain: {observed_domain}.",
        "es": "Dominio observado: {observed_domain}.",
    },
    "evidence.registration_date": {
        "en": "Registration date: {registration_date}.",
        "es": "Fecha de registro: {registration_date}.",
    },
    "evidence.computed_domain_age_days": {
        "en": "Computed domain age: {age_in_days} day(s).",
        "es": "Antigüedad calculada del dominio: {age_in_days} día(s).",
    },
    "evidence.lookup_provider": {
        "en": "Lookup provider: {provider_name}.",
        "es": "Proveedor de consulta: {provider_name}.",
    },
    "evidence.redirect_hops_observed": {
        "en": "Redirect hops observed: {hop_count}.",
        "es": "Saltos de redirección observados: {hop_count}.",
    },
    "evidence.final_url_after_redirects": {
        "en": "Final URL after redirects: {final_url}.",
        "es": "URL final tras las redirecciones: {final_url}.",
    },
    "evidence.redirect_resolver": {
        "en": "Redirect resolver: {provider_name}.",
        "es": "Resolvedor de redirecciones: {provider_name}.",
    },
    "evidence.redirect_chain_crossed_registered_domains": {
        "en": "Redirect chain crossed registered domains: {crossings}.",
        "es": "La cadena de redirección cruzó dominios registrados: {crossings}.",
    },
    "evidence.redirect_chain_downgraded_transport": {
        "en": "Redirect chain downgraded transport from HTTPS to HTTP.",
        "es": "La cadena de redirección degradó el transporte de HTTPS a HTTP.",
    },
    "evidence.final_destination_uses_questionable_tld": {
        "en": "Final destination uses a questionable TLD: .{tld}.",
        "es": "El destino final utiliza un TLD cuestionable: .{tld}.",
    },
    "evidence.listed_value": {
        "en": "Listed value: {value}.",
        "es": "Valor listado: {value}.",
    },
    "evidence.reputation_provider": {
        "en": "Reputation provider: {provider_name}.",
        "es": "Proveedor de reputación: {provider_name}.",
    },
    "evidence.provider_references": {
        "en": "Provider references: {reference_count}.",
        "es": "Referencias del proveedor: {reference_count}.",
    },
    "evidence.urlhaus_records": {
        "en": "URLhaus returned {reference_count} malicious URL record(s) for the queried host.",
        "es": "URLhaus devolvió {reference_count} registro(s) de URL maliciosa para el host consultado.",
    },
    "evidence.final_redirect_target": {
        "en": "Final redirect target: {final_url}.",
        "es": "Destino final de la redirección: {final_url}.",
    },
    "evidence.effective_target_host": {
        "en": "Effective target host: {host}.",
        "es": "Host del destino efectivo: {host}.",
    },
    "evidence.infrastructure_provider": {
        "en": "Infrastructure provider: {provider_name}.",
        "es": "Proveedor de infraestructura: {provider_name}.",
    },
    "evidence.resolved_addresses": {
        "en": "Resolved addresses: {addresses}.",
        "es": "Direcciones resueltas: {addresses}.",
    },
    "evidence.matched_infrastructure_patterns": {
        "en": "Matched infrastructure patterns: {patterns}.",
        "es": "Patrones de infraestructura coincidentes: {patterns}.",
    },
    "evidence.reverse_dns_sample": {
        "en": "Reverse DNS sample: {reverse_hostname}.",
        "es": "Muestra de DNS inverso: {reverse_hostname}.",
    },
    "evidence.matched_sensitive_url_terms": {
        "en": "Matched sensitive URL terms: {terms}.",
        "es": "Términos sensibles de URL coincidentes: {terms}.",
    },
    "evidence.effective_target_derived_from_redirect_chain": {
        "en": "Effective target derived from redirect chain: {final_url}.",
        "es": "Destino efectivo derivado de la cadena de redirección: {final_url}.",
    },
    "evidence.observed_url_scheme": {
        "en": "Observed URL scheme: {scheme}.",
        "es": "Esquema URL observado: {scheme}.",
    },
    "evidence.observed_host": {
        "en": "Observed host: {host}.",
        "es": "Host observado: {host}.",
    },
    "evidence.validated_host": {
        "en": "Validated host: {host}.",
        "es": "Host validado: {host}.",
    },
    "evidence.validation_provider": {
        "en": "Validation provider: {provider_name}.",
        "es": "Proveedor de validación: {provider_name}.",
    },
    "evidence.tls_failure_reason": {
        "en": "TLS failure reason: {failure_reason}.",
        "es": "Motivo del fallo TLS: {failure_reason}.",
    },
    "evidence.html_forms_found": {
        "en": "HTML forms found: {form_count}.",
        "es": "Formularios HTML encontrados: {form_count}.",
    },
    "evidence.password_fields_found": {
        "en": "Password fields found: {password_field_count}.",
        "es": "Campos de contraseña encontrados: {password_field_count}.",
    },
    "evidence.matched_account_input_hints": {
        "en": "Matched account input hints: {hints}.",
        "es": "Indicadores coincidentes de campos de cuenta: {hints}.",
    },
    "evidence.matched_auth_input_hints": {
        "en": "Matched authentication input hints: {hints}.",
        "es": "Indicadores coincidentes de campos de autenticación: {hints}.",
    },
    "evidence.matched_login_wording": {
        "en": "Matched login wording: {terms}.",
        "es": "Texto coincidente de inicio de sesión: {terms}.",
    },
    "evidence.observed_form_action": {
        "en": "Observed form action: {action}.",
        "es": "Acción de formulario observada: {action}.",
    },
    "evidence.suspicious_form_action": {
        "en": "Suspicious form action: {action}.",
        "es": "Acción de formulario sospechosa: {action}.",
    },
    "evidence.visible_text_tokens_found": {
        "en": "Visible text tokens found: {visible_token_count}.",
        "es": "Tokens de texto visible encontrados: {visible_token_count}.",
    },
    "evidence.matched_placeholder_markers": {
        "en": "Matched placeholder markers: {markers}.",
        "es": "Marcadores coincidentes de página provisional: {markers}.",
    },
    "evidence.no_forms_or_meaningful_visible_copy": {
        "en": "The fetched landing page exposes no forms or meaningful visible copy.",
        "es": "La página de aterrizaje recuperada no expone formularios ni contenido visible con significado.",
    },
    "evidence.user_agent_profiles_compared": {
        "en": "Compared user-agent profiles: {left_profile} vs {right_profile}.",
        "es": "Perfiles de user-agent comparados: {left_profile} frente a {right_profile}.",
    },
    "evidence.user_agent_variant_token_counts": {
        "en": "Normalized visible-token counts: {left_profile}={left_tokens}, {right_profile}={right_tokens}.",
        "es": "Recuento de tokens visibles normalizados: {left_profile}={left_tokens}, {right_profile}={right_tokens}.",
    },
    "evidence.user_agent_variant_similarity": {
        "en": "Normalized token similarity between {left_profile} and {right_profile}: {similarity}.",
        "es": "Similitud de tokens normalizados entre {left_profile} y {right_profile}: {similarity}.",
    },
    "evidence.login_cues_observed_for_profiles": {
        "en": "Login-oriented HTML cues were observed for: {profiles}.",
        "es": "Se observaron indicios HTML orientados a inicio de sesión para: {profiles}.",
    },
    "evidence.low_information_profiles_observed": {
        "en": "Low-information or near-empty HTML was observed for: {profiles}.",
        "es": "Se observó HTML de baja información o casi vacío para: {profiles}.",
    },
    "evidence.resolved_final_url": {
        "en": "Resolved final URL: {final_url}.",
        "es": "URL final resuelta: {final_url}.",
    },
}
