"""DTO normalizado de persona, común a todos los repositorios heterogéneos."""

from pydantic import BaseModel

from app.modules.webhook.features.personas.enums import PersonStatus


class PersonDTO(BaseModel):
    """Persona normalizada lista para presentar al usuario."""

    full_name: str
    national_id: str | None
    status: PersonStatus
    location: str | None
    source: str
