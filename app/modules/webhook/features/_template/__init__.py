"""Plantilla de feature. El registry IGNORA carpetas con prefijo `_`.

Al copiar esta carpeta a `features/<tu_feature>/`, este `FEATURE` será
autodescubierto y aparecerá en el menú. TODO: renombra la clase importada.
"""

from app.modules.webhook.features._template.feature import TemplateFeature

FEATURE = TemplateFeature()
