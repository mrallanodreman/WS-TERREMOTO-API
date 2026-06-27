"""Construcción del cliente pywa por tenant."""

from pywa import WhatsApp

from app.core.config import get_settings
from app.modules.webhook.handlers import setup_echo
from app.modules.webhook.schemas import Tenant


def build_client(tenant: Tenant) -> WhatsApp:
    """Construye el cliente pywa del tenant y registra el handler de echo.

    Args:
        tenant: Credenciales (phone_id, token) del tenant del forward.

    Returns:
        Cliente pywa en modo sin servidor, listo para `webhook_update_handler`.
    """
    client = WhatsApp(
        server=None,
        phone_id=tenant.phone_id,
        token=tenant.token,
        app_secret=get_settings().whatsapp_app_secret,
    )
    setup_echo(client)
    return client
