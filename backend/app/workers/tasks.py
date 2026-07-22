from celery.utils.log import get_task_logger
from backend.app.db.session import SessionLocal
from backend.app.services.jobs import execute_job

from backend.app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="crawler_api.run_crawl_job")
def run_crawl_job(job_id: int) -> dict:
    logger.info("Received crawl job %s", job_id)
    db = SessionLocal()
    try:
        job = execute_job(db, job_id)
        return {"job_id": job.id, "status": job.status}
    finally:
        db.close()
