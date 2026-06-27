"""DTO normalizado de tu feature. TODO: define los campos de tu dominio."""

from pydantic import BaseModel


class ItemDTO(BaseModel):
    """Resultado normalizado listo para presentar. TODO: renómbralo y complétalo."""

    title: str
    detail: str | None
    source: str
