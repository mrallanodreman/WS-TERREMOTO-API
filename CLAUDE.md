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
│   ├── redis.py               # get_redis() — cliente Redis crudo (infra, sin dominio)
│   └── errors.py              # contrato de error único + handlers + request_id
├── modules/
│   └── webhook/               # módulo de dominio (8 archivos estándar)
│       ├── api.py             # endpoints; traduce excepción de dominio → HTTP
│       ├── services.py        # lógica (no sabe de HTTP)
│       ├── client.py          # construye el WhatsApp (pywa) del tenant
│       ├── handlers.py        # @wa.on_message → delega en ConversationService
│       ├── outgoing.py        # patch GraphAPI.send_message → bound a ws-backend
│       ├── schemas.py         # DTOs (pydantic)
│       ├── enums.py           # valores cerrados (StrEnum)
│       ├── exceptions.py      # excepciones de dominio
│       ├── messages.py        # mensajes de error HTTP (inglés, centralizados)
│       ├── conversation/      # motor del bot de menú (ver §10)
│       │   ├── contracts.py   # Protocol Feature + FeatureTurn/FeatureReply
│       │   ├── service.py     # dispatcher: menú ↔ feature, carga/persiste estado
│       │   ├── store.py       # ConversationStore (Redis + InMemory) por (tenant,user)
│       │   ├── registry.py    # autodescubrimiento de features
│       │   ├── schemas.py     # ConversationState + conversation_key()
│       │   ├── enums.py       # comandos globales (menú/0/salir)
│       │   └── messages.py    # copy del menú hacia el usuario (ESPAÑOL)
│       └── features/          # las opciones del menú (1 carpeta = 1 feature)
│           ├── personas/      # feature de referencia (repo→mapper→presenter)
│           └── _template/     # plantilla para nuevos features (el `_` la ignora)
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

> El handler real (`setup_handlers`) ya **delega en `ConversationService`** (el motor del
> bot de menú, §10): extrae `tenant.phone_id` + `msg.from_user.wa_id`, arma la clave de
> conversación y responde con `msg.reply_text(service.handle_text(...))`. El *qué hacemos*
> no vive en el handler sino en el motor y en cada **feature**.

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
  `WHATSAPP_APP_SECRET`, `ENCRYPTION_SECRET_KEY`, `WEBHOOK_ADD_MESSAGE_ENDPOINT`,
  `REDIS_URL` (estado de conversación; ver §10).
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

---

## 10. Crear un feature de menú (el bot lineal)

El bot ya no hace echo: presenta un **menú** ("1) Búsqueda de personas, 2) …") y cada
opción es un **feature**. Un feature **no es un módulo de dominio HTTP** (§3): no tiene
`api.py`, router ni excepciones HTTP. Es una carpeta autocontenida en
`app/modules/webhook/features/<feature>/` que implementa el `Protocol` `Feature`.

### Cómo funciona el motor (`webhook/conversation/`)

```
WhatsApp → handler → ConversationService.handle_text(key, text)
  key = conversation_key(tenant.phone_id, msg.from_user.wa_id)
  1. comando global (menú/menu/0/salir) → limpia estado → muestra menú
  2. sin feature activo → interpreta el texto como nº de opción → feature.start()
  3. con feature activo → feature.handle(turn) → si done, vuelve al menú
```

- **Estado en Redis** (`ConversationStore`, TTL 30 min deslizante), keyed por
  `(tenant phone_id, user wa_id)`. Es **obligatorio externo**: `build_client` reconstruye
  el cliente pywa en cada request y hay varios workers, así que la memoria del proceso (y
  los *listeners* nativos de pywa) **no sirven**.
- El cliente Redis crudo es **infra** → `core/redis.py::get_redis()`. El `ConversationStore`
  (serializa `ConversationState`, dominio) vive en `conversation/store.py` (modules→core).

### El contrato (`conversation/contracts.py`)

```python
class MiFeature:
    key = "mi_feature"          # único y estable (snake_case); NO cambiarlo luego
    label = "Texto en el menú"
    order = 2                   # posición; desempate alfabético por key

    def start(self) -> FeatureReply:                 # primer mensaje al entrar
        return FeatureReply(text="...", step="paso_1")

    def handle(self, turn: FeatureTurn) -> FeatureReply:   # cada respuesta del usuario
        ...                                          # done=True → vuelve al menú
```

`FeatureTurn{text, step, data}` entra; `FeatureReply{text, step, data, done}` sale. El motor
solo persiste `feature/step/data`; flujos multi-paso leen `turn.step` y acumulan en
`turn.data`. Los comandos globales (volver al menú) los maneja el motor: gratis.

### Capa de datos: `repository → mapper → presenter` (regla de tres aplicada)

- `repository.py`: una clase **por fuente** (API/DB) con `search(query) -> list[DTO]` que
  devuelve **DTOs ya normalizados**. Fuentes heterogéneas = varias clases repo; el feature
  concatena sus DTOs y el `presenter` no sabe de fuentes.
- `mapper.py`: traduce el registro crudo de la fuente → DTO de dominio (`schemas.py`).
- `presenter.py`: DTOs → texto de WhatsApp.
- `messages.py` del feature: **copy hacia el usuario, en español** (≠ los `messages.py` de
  error HTTP, que van en inglés, §4). `enums.py`: valores cerrados (`StrEnum`).

### Registro = cero archivos compartidos

El feature se **autodescubre**: basta que su `__init__.py` exponga `FEATURE = MiFeature()`.
No se edita ninguna lista ni router → **PRs en paralelo sin conflictos de merge**. Las
carpetas con prefijo `_` (como `_template`) se ignoran.

### Plantilla y guía

Copia `features/_template/` → `features/<tu_feature>/`, renómbrala y sigue su `README.md`.
Todo feature entra con sus tests (`repository`/`mapper`/`presenter`; ver `tests/test_personas.py`)
y debe pasar los 4 gates (§7). El contrato `forbidden` de import-linter impide que un
feature toque `client`/`outgoing`.

> **pywa:** consultar siempre la doc oficial — https://pywa.readthedocs.io/. El menú hoy es
> texto numérico (todas las salidas son `type: text`, lo que mantiene intacto el bound de
> `outgoing.py`); es migrable a lista interactiva (`SectionList` + `on_callback_selection`)
> sin cambiar el contrato `Feature`.
