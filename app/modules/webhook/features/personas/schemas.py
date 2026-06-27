"""DTO normalizado de persona, común a todos los repositorios heterogéneos."""

from pydantic import BaseModel

from app.modules.webhook.features.personas.enums import PersonStatus


class PersonDTO(BaseModel):
    """Persona normalizada lista para presentar al usuario."""

    report_id: str | None
    full_name: str
    status: PersonStatus
    location: str | None
    message: str | None
    source: str | None
    source_url: str | None
