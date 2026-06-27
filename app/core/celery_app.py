"""Instancia de Celery: procesamiento asíncrono del webhook fuera del request."""

import logging
import time

from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

celery_app = Celery(
    "ws_terremoto",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.modules.webhook.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_default_queue="fast",  # las colas fast/heavy se eligen por apply_async (ver §11)
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    task_soft_time_limit=540,
    task_time_limit=600,
)


_task_start_times: dict[str, float] = {}


@task_prerun.connect  # type: ignore[untyped-decorator]  # celery: señales sin tipos
def _on_task_prerun(task_id: str, task: object, **_: object) -> None:
    """Marca el inicio del task para medir su duración."""
    _task_start_times[task_id] = time.monotonic()


@task_postrun.connect  # type: ignore[untyped-decorator]  # celery: señales sin tipos
def _on_task_postrun(task_id: str, task: object, state: str, **_: object) -> None:
    """Loguea la duración del task al terminar."""
    elapsed = time.monotonic() - _task_start_times.pop(task_id, time.monotonic())
    logger.info("[CELERY] task=%s state=%s duration=%.3fs", task_id, state, elapsed)


@task_failure.connect  # type: ignore[untyped-decorator]  # celery: señales sin tipos
def _on_task_failure(task_id: str, exception: BaseException, **_: object) -> None:
    """Loguea el fallo del task con su contexto."""
    elapsed = time.monotonic() - _task_start_times.pop(task_id, time.monotonic())
    logger.error(
        "[CELERY] task=%s FAILED error=%s duration=%.3fs", task_id, exception, elapsed
    )
