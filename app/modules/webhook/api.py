"""Endpoints del webhook; traduce excepciones de dominio a HTTP."""

from fastapi import APIRouter, Request, Response, status

from app.core.errors import DomainHTTPException
from app.modules.webhook import messages
from app.modules.webhook.exceptions import (
    InvalidCredentialsError,
    InvalidSignatureError,
    MissingCredentialsError,
    WebhookError,
)
from app.modules.webhook.services import WebhookService

router = APIRouter()

_DOMAIN_HTTP_ERRORS: dict[type[WebhookError], tuple[int, str, str]] = {
    InvalidSignatureError: (
        status.HTTP_403_FORBIDDEN,
        "INVALID_SIGNATURE",
        messages.INVALID_SIGNATURE,
    ),
    MissingCredentialsError: (
        status.HTTP_401_UNAUTHORIZED,
        "MISSING_CREDENTIALS",
        messages.MISSING_CREDENTIALS,
    ),
    InvalidCredentialsError: (
        status.HTTP_401_UNAUTHORIZED,
        "INVALID_CREDENTIALS",
        messages.INVALID_CREDENTIALS,
    ),
}


def _as_http_error(exc: WebhookError) -> DomainHTTPException:
    status_code, code, detail = _DOMAIN_HTTP_ERRORS[type(exc)]
    return DomainHTTPException(status_code=status_code, code=code, detail=detail)


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "healthy"}


@router.post("/webhook")
async def webhook(request: Request) -> Response:
    """Verifica el forward firmado de ws-backend y encola su procesamiento."""
    body = await request.body()
    try:
        WebhookService().enqueue(
            body,
            request.headers.get("X-Hub-Signature-256"),
            request.headers.get("Authorization"),
        )
    except WebhookError as exc:
        raise _as_http_error(exc) from None
    return Response(content="ok", status_code=status.HTTP_200_OK, media_type="text/plain")
