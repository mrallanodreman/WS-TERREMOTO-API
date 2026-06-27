"""DTOs del módulo webhook."""

from pydantic import BaseModel


class Tenant(BaseModel):
    """Credenciales mínimas del tenant para responder por su número."""

    phone_id: str
    token: str
