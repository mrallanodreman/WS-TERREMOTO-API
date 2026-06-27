"""Copy del feature de búsqueda de personas hacia el usuario (español)."""

PROMPT_QUERY = (
    "Escribe el *nombre* (o parte del nombre) de la persona que buscas.\n"
    "Reviso los reportes de personas desaparecidas y de quienes se reportaron."
)
NO_RESULTS = "No encontré coincidencias. Verifica el nombre e inténtalo de nuevo."
SERVICE_UNAVAILABLE = (
    "No pude consultar la base de personas en este momento. "
    "Inténtalo de nuevo en unos minutos."
)
RESULTS_HEADER = "Esto fue lo que encontré:"
STATUS_SAFE = "✅ A salvo"
STATUS_NEEDS_HELP = "🆘 Necesita ayuda"
STATUS_LOOKING_FOR_SOMEONE = "🔴 Reportada como desaparecida"
STATUS_UNKNOWN = "⚪ Estado desconocido"
SOURCE_PREFIX = "Fuente"
