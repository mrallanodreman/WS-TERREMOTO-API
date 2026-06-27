# WS-TERREMOTO-API — Cómo se trabaja en este repo

Webhook **multitenant** de WhatsApp construido con **pywa**. Recibe el forward
firmado de `ws-backend`, identifica el tenant por las credenciales cifradas, y
responde vía pywa. Cada salida se reenvía (bound) a `ws-backend` para guardarla.

Hoy solo hace **echo**; de aquí en adelante el comportamiento se agrega en los
**handlers** y la lógica en los **services**, respetando la estructura de abajo.

---

## 0. Reglas rectoras

1. **Sin comentarios de relleno.** Código claro con nombres que se entiendan
   solos. Solo comentar lógica de muy bajo nivel o un *por qué* no obvio.
2. **Disciplina = gate de CI.** Nada se mergea si no pasa los 4 gates (§7).
3. **Regla de tres:** la primera vez se escribe inline; la segunda se anota; a la
   **tercera** se extrae a `app/core/` y todos consumen esa pieza. No se copia-pega
   lógica entre módulos.
4. **Capas en una sola dirección:** `api → services → (client/handlers) → core`.
   El endpoint no mete lógica; el service no sabe de HTTP; `core/` no importa de
   `modules/`. Lo verifica `import-linter`.
5. **Config solo por `get_settings()`** (§5). Nunca `os.getenv` suelto.
6. **Cero strings mágicos de dominio:** valores cerrados → `StrEnum` en `enums.py`.

---

## 1. Estructura

```
app/
├── core/                      # infra compartida, NO dominio
│   ├── config.py              # Settings (pydantic-settings) — único lector de .env
│   ├── security.py            # firma del forward + descifrado de credenciales
│   └── errors.py              # contrato de error único + handlers + request_id
├── modules/
│   └── webhook/               # módulo de dominio (8 archivos estándar)
│       ├── api.py             # endpoints; traduce excepción de dominio → HTTP
│       ├── services.py        # lógica (no sabe de HTTP)
│       ├── client.py          # construye el WhatsApp (pywa) del tenant
│       ├── handlers.py        # @wa.on_message / @wa.on_callback_button → delega a services
│       ├── outgoing.py        # patch GraphAPI.send_message → bound a ws-backend
│       ├── schemas.py         # DTOs (pydantic)
│       ├── enums.py           # valores cerrados (StrEnum)
│       ├── exceptions.py      # excepciones de dominio
│       └── messages.py        # mensajes de error (inglés, centralizados)
├── api/router.py              # ensambla los routers
└── main.py                    # crea la app, middleware, handlers de error, routers
```

`core/` = infra sin reglas de negocio · `modules/` = el dominio · `api/` solo ensambla.

---

## 2. Handlers (el corazón del proyecto)

Toda interacción de WhatsApp entra por un **handler de pywa**. Aquí se decide
*qué eventos escuchamos*; el *qué hacemos* vive en `services.py`.

### Reglas de los handlers

- Viven en `app/modules/webhook/handlers.py` y se registran en **una** función
  `setup_*(wa)` que `client.py::build_client` llama al crear el cliente del tenant.
- **El handler es fino: recibe el update, extrae lo mínimo y delega a un service.**
  Nada de lógica de negocio, llamadas a APIs externas ni `if` de dominio dentro del
  handler. Si el handler crece, la lógica va a `services.py`.
- Ignorar lo que no se procesa (tipos no soportados) temprano y salir.
- Loguear la entrada con `msg.id` + `phone` para trazar.

### Patrón para agregar un handler nuevo

```python
# handlers.py
def setup_handlers(wa: WhatsApp) -> None:
    """Registra todos los handlers del webhook."""

    @wa.on_message()  # type: ignore[untyped-decorator]  # pywa: decorador sin tipos
    def on_message(client: WhatsApp, msg: types.Message) -> None:
        logger.info("[WEBHOOK:IN] [%s] phone=%s type=%s", msg.id, msg.from_user.wa_id, msg.type.value)
        if not msg.text:
            return
        WebhookService().handle_text(msg)        # ← delega; la lógica va en el service

    @wa.on_callback_button()  # type: ignore[untyped-decorator]
    def on_button(client: WhatsApp, cb: types.CallbackButton) -> None:
        WebhookService().handle_button(cb)
```

> Hoy `setup_echo` hace el echo inline porque es trivial (una línea). En cuanto la
> respuesta deje de ser un echo, se renombra a `setup_handlers` y el handler pasa a
> **delegar en `WebhookService`** en vez de responder directo.

### Enviar mensajes

Siempre por pywa (`msg.reply_text(...)`, `client.send_message(...)`). **No** armar
requests HTTP a la Graph API a mano: el `outgoing.py` parchea `send_message` para
hacer el bound a `ws-backend` automáticamente en cada salida. Si lo evitas, te
saltas el guardado.

---

## 3. Agregar un módulo de dominio nuevo

Cuando aparezca un dominio distinto del webhook (p. ej. `flows`, `admin`), se crea
`app/modules/<modulo>/` con **los mismos 8 archivos** del §1 (los que apliquen) y:

1. Su router se incluye en `app/api/router.py`.
2. Sus excepciones de dominio se mapean a HTTP en su `api.py` (§4).
3. Se agrega su contrato `forbidden` en `pyproject.toml` para que nadie importe
   sus internals (`models`/`repositories`/`services` privados):

```toml
[[tool.importlinter.contracts]]
name = "Nadie importa internals de webhook"
type = "forbidden"
source_modules = ["app.modules.<otro_modulo>"]
forbidden_modules = ["app.modules.webhook.client", "app.modules.webhook.outgoing"]
```

Un módulo solo consume de otro su superficie pública: `services`, `enums`, `exceptions`.

---

## 4. Errores: dominio → HTTP

- Los services levantan **excepciones de dominio** (`exceptions.py`), sin saber de
  HTTP. Los mensajes viven en `messages.py` (inglés, centralizados).
- `api.py` traduce con un **mapping único** `excepción → (status, code, message)` y
  levanta `DomainHTTPException`. Agregar un error = una clase + una línea en
  `messages.py` + una línea en el mapping. El endpoint no cambia.
- Toda respuesta de error sale con el **contrato único** (definido en `core/errors.py`):
  ```json
  { "error": { "code": "INVALID_SIGNATURE", "message": "...", "request_id": "..." } }
  ```
  En 5xx **nunca** se filtra el detalle interno; siempre va el `request_id`.

---

## 5. Config y secretos

- Todo entra por `app/core/config.py::Settings` y se lee con `get_settings()`.
- Variables actuales (las dos primeras **idénticas** a `ws-backend`):
  `WHATSAPP_APP_SECRET`, `ENCRYPTION_SECRET_KEY`, `WEBHOOK_ADD_MESSAGE_ENDPOINT`.
- `.env` **nunca** se commitea (está en `.gitignore`); se versiona `.env.example`.
- Variable nueva = se declara y tipa en `Settings`, se documenta en `.env.example`.

---

## 6. Multitenancy (cómo llega cada request)

```
Meta → ws-backend → (forward firmado) → POST /ms/ws/webhook
   1. verify_signature  (X-Hub-Signature-256 con WHATSAPP_APP_SECRET)
   2. resolve_tenant    (Authorization cifrado → phone_id, token)   ← core/security.py
   3. build_client      (pywa con las credenciales del tenant)      + registra handlers
   4. webhook_update_handler(body)                                  → dispara los handlers
```

El `phone_id`/`token` salen del tenant del forward, **no** de variables globales:
así un mismo servicio responde por múltiples números/empresas.

---

## 7. Gates de calidad (obligatorios)

```bash
.venv/bin/ruff check app tests     # formato + lint + docstrings (google) + strings mágicos
.venv/bin/mypy                     # tipado estricto (app 100%; tests relajado por override)
.venv/bin/lint-imports             # capas api → modules → core
.venv/bin/pytest                   # tests + cobertura (mínimo 80%)
```

- Los tests cubren el flujo real (echo+bound, firma inválida, credenciales). Todo
  comportamiento nuevo entra con su test.
- `app/` debe quedar **strict-clean**. Los `# type: ignore` sobre pywa (sin stubs)
  van **siempre con su motivo** al lado.

---

## 8. Correr y desplegar

```bash
# dev (reload)
export $(grep -v '^#' .env | xargs) ; .venv/bin/python3 -m uvicorn app.main:app --reload --port 8001

# producción local (gunicorn + workers uvicorn)
export $(grep -v '^#' .env | xargs) ; .venv/bin/gunicorn app.main:app -c gunicorn.conf.py

# docker (usa gunicorn)
docker compose up -d --build
```

- En contenedor corre con **gunicorn** (`gunicorn.conf.py`); la concurrencia la dan
  los `WORKERS` (pywa es síncrono/bloqueante).
- **Deploy:** Dokploy propio, tipo Application/Dockerfile, puerto `8000`, las 3 env
  vars, dominio con HTTPS y healthcheck `/ms/ws/health`. URL del webhook resultante:
  `https://<dominio>/ms/ws/webhook`.

> **Prefijo del microservicio:** todas las rutas cuelgan de `/ms/ws/`, definido en
> `app/api/router.py` (`APIRouter(prefix="/ms/ws")`). Un endpoint nuevo se declara
> con su path normal (`/webhook`) y hereda el prefijo automáticamente.

---

## 9. Commits

Conventional Commits: `feat(webhook): …`, `fix(webhook): …`, `chore: …`.
Una migración/cambio coherente por PR. No mergear lógica duplicada (§0, regla de tres).
