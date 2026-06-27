"""Excepciones de dominio del módulo webhook."""


class WebhookError(Exception):
    """Base de todas las excepciones de dominio del módulo webhook."""


class InvalidSignatureError(WebhookError):
    """La firma del forward no coincide con el app_secret compartido."""


class MissingCredentialsError(WebhookError):
    """No llegó el header `Authorization` con las credenciales del tenant."""


class InvalidCredentialsError(WebhookError):
    """Las credenciales del tenant no se pudieron descifrar o están incompletas."""
