"""Ensamblado de los routers de la API."""

from fastapi import APIRouter

from app.modules.webhook.api import router as webhook_router

api_router = APIRouter(prefix="/ms/ws")
api_router.include_router(webhook_router)
