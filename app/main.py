"""Punto de entrada: crea la app FastAPI y registra todo."""

from fastapi import FastAPI

from app.api.router import api_router
from app.core.errors import RequestIDMiddleware, register_error_handlers
from app.modules.webhook import outgoing  # noqa: F401  activa el patch de salida


def create_app() -> FastAPI:
    """Crea la app, registra middleware, handlers de error y routers."""
    app = FastAPI(title="WS-TERREMOTO-API")
    app.add_middleware(RequestIDMiddleware)
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
