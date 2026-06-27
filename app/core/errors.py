"""Contrato de error único y handlers globales de la app."""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)

INTERNAL_ERROR = "INTERNAL_ERROR"
VALIDATION_ERROR = "VALIDATION_ERROR"

_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}


class DomainHTTPException(StarletteHTTPException):
    """HTTPException que transporta el `code` de dominio para el contrato §6."""

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        """Construye la excepción con su `code` de dominio."""
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


def _status_to_code(status_code: int) -> str:
    return _STATUS_CODES.get(status_code, INTERNAL_ERROR)


def _payload(
    code: str,
    message: str,
    *,
    fields: dict[str, list[str]] | None = None,
    request_id: str = "",
) -> dict[str, object]:
    err: dict[str, object] = {"code": code, "message": message, "request_id": request_id}
    if fields:
        err["fields"] = fields
    return {"error": err}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Asigna un `request_id` único por petición para correlación con logs."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Inyecta el `request_id` y lo devuelve en el header de respuesta."""
        request.state.request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


def register_error_handlers(app: FastAPI) -> None:
    """Registra el contrato de error único para toda la app."""

    @app.exception_handler(RequestValidationError)
    async def _on_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields: dict[str, list[str]] = {}
        for e in exc.errors():
            loc = ".".join(str(p) for p in e["loc"] if p != "body")
            fields.setdefault(loc, []).append(e["msg"])
        return JSONResponse(
            status_code=422,
            content=_payload(
                VALIDATION_ERROR,
                "Validation failed",
                fields=fields,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _on_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = getattr(exc, "code", None) or _status_to_code(exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(code, str(exc.detail), request_id=_request_id(request)),
        )

    @app.exception_handler(Exception)
    async def _on_unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error request_id=%s", _request_id(request))
        return JSONResponse(
            status_code=500,
            content=_payload(
                INTERNAL_ERROR, "Internal server error", request_id=_request_id(request)
            ),
        )
