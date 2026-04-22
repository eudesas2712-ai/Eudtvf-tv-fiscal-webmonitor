from celery import Celery
from app.core.config import settings

celery = Celery(
    "webmonitor",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.task_serializer = "json"
celery.conf.result_serializer = "json"
celery.conf.accept_content = ["json"]
celery.conf.timezone = "America/Fortaleza"