# Cómo crear un feature de menú

Un **feature** es una opción del menú del bot (ej. "Búsqueda de personas"). Es una
carpeta autocontenida en `features/`. **No edites ningún archivo compartido**: con solo
crear la carpeta, el autodescubrimiento lo agrega al menú (cero conflictos de merge).

## Pasos

1. **Copia esta carpeta** a `features/<tu_feature>/` (nombre en `snake_case`, sin `_`).
   El prefijo `_` solo lo usa esta plantilla para que el registry la ignore.
2. En `feature.py` **renombra la clase** (`TemplateFeature` → `TuFeature`) y ajusta:
   - `key`: identificador único y estable (`snake_case`). **No lo cambies después**: es
     la clave del estado de conversación.
   - `label`: el texto que ve el usuario en el menú.
   - `order`: posición en el menú (entero). Rango sugerido por equipo para no chocar;
     si dos features comparten `order`, el desempate es alfabético por `key`.
3. En `__init__.py` ajusta el import y deja `FEATURE = TuFeature()`.
4. Implementa tu **capa de datos** (patrón `repository → mapper → presenter`):
   - `repository.py`: una clase por fuente (API/DB) que implementa `search()` y devuelve
     **DTOs ya normalizados**. Borra el stub cuando conectes la fuente real.
   - `mapper.py`: traduce el registro crudo de tu fuente al DTO de dominio.
   - `presenter.py`: convierte la lista de DTOs en el texto de WhatsApp.
   - `schemas.py` / `enums.py`: tu DTO y tus valores cerrados (`StrEnum`).
   - `messages.py`: tu copy hacia el usuario, **en español**.
5. **Varias fuentes heterogéneas**: agrega una clase repo + su mapper por cada una y
   pásalas en la tupla del constructor de tu feature. El presenter no sabe de fuentes.

## El contrato (`conversation/contracts.py`)

Tu clase implementa el `Protocol` `Feature`:

- `key`, `label`, `order`
- `start() -> FeatureReply`: primer mensaje al entrar.
- `handle(turn: FeatureTurn) -> FeatureReply`: procesa cada respuesta.

`FeatureTurn{text, step, data}` entra; `FeatureReply{text, step, data, done}` sale.
El motor solo persiste `feature/step/data`. **Flujos de varios pasos**: lee `turn.step`,
acumula en `turn.data`, devuelve `FeatureReply(step=..., data=...)`. Cuando termines,
`done=True` → el usuario vuelve al menú.

## Comandos globales (gratis)

El motor maneja `menú` / `menu` / `0` / `salir` para volver al menú desde cualquier paso.
No tienes que implementarlos.

## Checklist antes del PR

```bash
.venv/bin/ruff check app tests
.venv/bin/mypy
.venv/bin/lint-imports
.venv/bin/pytest
```

Agrega tests de tu `repository`, `mapper` y `presenter` (mira `tests/test_personas.py`).
