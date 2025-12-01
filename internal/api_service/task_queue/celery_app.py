from __future__ import annotations

import os

from celery import Celery

# Broker/backend defaults can be overridden via env vars when running locally or in Docker
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

celery_app = Celery(
  "segmentation_scheduler",
  broker=BROKER_URL,
  backend=BACKEND_URL
)

celery_app.conf.update(
  task_serializer="json",
  accept_content=["json"],
  result_serializer="json",
  timezone="UTC",
  enable_utc=True,
  task_acks_late=True,
)

# Make sure workers can discover tasks when launched via `celery -A task_queue.celery_app worker`
celery_app.autodiscover_tasks(["task_queue", "internal.api_service.task_queue"])
