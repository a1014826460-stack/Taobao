from celery.utils.log import get_task_logger

from backend.app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="crawler_api.run_crawl_job")
def run_crawl_job(job_id: int) -> dict:
    # The API persists jobs before dispatch. A worker deployment can replace this
    # deterministic placeholder with the registered direct/proxy service adapter.
    logger.info("Received crawl job %s", job_id)
    return {"job_id": job_id, "status": "queued-for-worker"}
