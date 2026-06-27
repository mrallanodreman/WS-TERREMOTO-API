# WS-TERREMOTO-API

> ## 🟢 En vivo — ¡pruébalo!
>
> **Ayuda Venezuela** ya está activo en WhatsApp. Escríbele para probar el bot:
>
> ### 📲 **0422 163 6078**
>
> 👉 [**Abrir chat en WhatsApp**](https://wa.me/584221636078) · manda cualquier mensaje
> y te responde el **menú** de opciones (hoy: *Búsqueda de personas*).

Webhook multitenant de WhatsApp (**pywa**) que recibe el forward firmado de
`ws-backend`, identifica el tenant por sus credenciales cifradas y responde con un
**bot lineal de menú**: cada opción es un **feature** contribuible (búsqueda de
personas, centros de acopio, refugios…). Cada salida se reenvía (bound) a `ws-backend`.

Estructurado según el boilerplate de disciplina FastAPI (capas `app/{core,modules,api}`,
config única, excepciones de dominio → HTTP, contrato de error único, tooling como gate de CI).

> **¿Quieres aportar un módulo?** Cada opción del menú es una carpeta autocontenida en
> `app/modules/webhook/features/`. Copia `features/_template/`, impleméntala y abre tu PR
> — no editas nada compartido. Guía completa en
> [`features/_template/README.md`](app/modules/webhook/features/_template/README.md) y en
> la sección §10 de [`CLAUDE.md`](CLAUDE.md).

## Estructura

```
WS-TERREMOTO-API/
├── app/
│   ├── core/                      # infra compartida, NO dominio
│   │   ├── config.py              # Settings (pydantic-settings) — único lector de .env
│   │   ├── security.py            # firma del forward + descifrado de credenciales
│   │   └── errors.py              # contrato de error único + handlers + request_id
│   │   ├── redis.py              # get_redis() — cliente Redis (estado de conversación)
│   ├── modules/
│   │   └── webhook/               # módulo de dominio
│   │       ├── api.py             # endpoints; traduce excepciones → HTTP
│   │       ├── services.py        # lógica (firma, tenant, procesa el update)
│   │       ├── client.py          # construye el WhatsApp (pywa) del tenant
│   │       ├── handlers.py        # @wa.on_message → delega en ConversationService
│   │       ├── outgoing.py        # patch GraphAPI.send_message → bound a ws-backend
│   │       ├── schemas.py         # Tenant (DTO)
│   │       ├── enums.py           # valores cerrados de la API de WhatsApp
│   │       ├── exceptions.py      # excepciones de dominio
│   │       ├── messages.py        # mensajes de error (inglés, centralizados)
│   │       ├── conversation/      # motor del bot de menú (estado en Redis)
│   │       └── features/          # opciones del menú (1 carpeta = 1 feature) + _template/
│   ├── api/router.py              # ensambla los routers
│   └── main.py                    # crea la app, middleware, handlers y routers
├── tests/                         # pytest (echo+bound, firma, credenciales)
├── pyproject.toml                 # ruff + mypy --strict + pytest + import-linter
├── requirements.txt               # dependencias de runtime
└── .env.example
```

## Flujo

```
Meta ──► ws-backend ──(forward firmado)──► POST /ms/ws/webhook
                                              │ verify_signature (X-Hub-Signature-256)
                                              │ resolve_tenant   (Authorization cifrado)
                                              │ build_client     (pywa, credenciales del tenant)
                                              ▼ webhook_update_handler
                                           @wa.on_message → ConversationService
                                              │ carga estado (Redis) por (tenant, usuario)
                                              │ menú ↔ feature activo → reply_text
                                              │
                              patch send_message ─► bound a ws-backend (con wamid)
```

El estado de conversación (en qué opción/paso está cada usuario) vive en **Redis**,
keyed por `(tenant phone_id, usuario wa_id)` con TTL deslizante: así un mismo servicio
atiende múltiples números/empresas y escala con varios workers de gunicorn.

## Variables de entorno (`.env`)

Las dos primeras deben ser **idénticas** a las de `ws-backend`:

- `WHATSAPP_APP_SECRET` — valida la firma del forward.
- `ENCRYPTION_SECRET_KEY` — descifra las credenciales del tenant.
- `WEBHOOK_ADD_MESSAGE_ENDPOINT` — endpoint de `ws-backend` para guardar el saliente.
- `REDIS_URL` — estado de conversación del bot de menú. En local: `redis://localhost:6379/0`;
  en Docker el contenedor `api` apunta a `redis://redis:6379/0`.

Toda variable entra por `app/core/config.py` (`get_settings()`); ningún módulo usa `os.getenv` suelto.

## Correr

### Local (dev, con reload)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export $(grep -v '^#' .env | xargs) ; .venv/bin/python3 -m uvicorn app.main:app --reload --port 8001
```

### Local (producción, gunicorn)

```bash
export $(grep -v '^#' .env | xargs) ; .venv/bin/gunicorn app.main:app -c gunicorn.conf.py
```

### Docker (usa gunicorn)

```bash
cp .env.example .env          # completar con los valores reales
docker compose up -d --build  # levanta la API en http://localhost:8001
docker compose logs -f        # ver logs
docker compose down           # bajar
```

El servicio expone `8001` (host) → `8000` (contenedor) y trae healthcheck sobre `/ms/ws/health`.

> **Todas las rutas viven bajo el prefijo `/ms/ws/`** → `/ms/ws/webhook` y `/ms/ws/health`.

## Servidor (gunicorn)

En contenedor/producción corre con **gunicorn + workers uvicorn** (`gunicorn.conf.py`).
Todo se ajusta por variables de entorno:

| Var | Default | Qué controla |
|---|---|---|
| `WORKERS` | `cpu*2+1` | Número de workers |
| `PORT` | `8000` | Puerto de bind dentro del contenedor |
| `GUNICORN_TIMEOUT` | `30` | Timeout por request (s) |
| `GRACEFUL_TIMEOUT` | `10` | Espera al reiniciar workers (s) |
| `MAX_REQUESTS` / `MAX_REQUESTS_JITTER` | `2000` / `200` | Recicla workers para evitar fugas de memoria |
| `LOG_LEVEL` | `info` | Nivel de log |

El procesamiento de pywa es síncrono y bloqueante, así que la concurrencia real
la dan los **workers**: súbelos con `WORKERS` según CPU y carga esperada.

## Gates de calidad (CI)

```bash
.venv/bin/pip install -r requirements.txt ruff mypy pytest pytest-cov import-linter
.venv/bin/ruff check app tests       # formato + lint + docstrings + strings mágicos
.venv/bin/mypy                       # tipado estricto
.venv/bin/lint-imports               # capas api → modules → core
.venv/bin/pytest                     # tests + cobertura (mínimo 80%)
```

> Al agregar un módulo nuevo: repetir los 8 archivos estándar y añadir su contrato
> `forbidden` en `[tool.importlinter]` para que nadie importe sus internals.
