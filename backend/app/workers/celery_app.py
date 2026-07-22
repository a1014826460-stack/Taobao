from celery import Celery

from backend.app.core.config import get_settings

settings = get_settings()
celery_app = Celery("crawler_api", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_track_started = True
