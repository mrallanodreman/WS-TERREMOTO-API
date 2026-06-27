"""Autodescubrimiento de features: cada subpaquete de `features` expone FEATURE."""

import importlib
import pkgutil
from functools import lru_cache

from app.modules.webhook import features
from app.modules.webhook.conversation.contracts import Feature


@lru_cache
def discover_features() -> dict[str, Feature]:
    """Importa cada subpaquete de `features` (ignora prefijo `_`) y recolecta su FEATURE."""
    found: dict[str, Feature] = {}
    for info in pkgutil.iter_modules(features.__path__, f"{features.__name__}."):
        leaf = info.name.rsplit(".", 1)[-1]
        if leaf.startswith("_"):
            continue
        module = importlib.import_module(info.name)
        feature: Feature = module.FEATURE
        found[feature.key] = feature
    return found
