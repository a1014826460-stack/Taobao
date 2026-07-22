from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.models.job import CrawlJob
from backend.app.models.user import User


def create_job(
    db: Session,
    user: User,
    crawler: str,
    input: dict,
    credential_profile_id: int | None = None,
    proxy_profile_id: int | None = None,
) -> CrawlJob:
    job = CrawlJob(
        user_id=user.id,
        crawler=crawler,
        input=input,
        credential_profile_id=credential_profile_id,
        proxy_profile_id=proxy_profile_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def complete_job(db: Session, job: CrawlJob, result: dict) -> CrawlJob:
    job.status = "succeeded"
    job.result = result
    job.completed_at = datetime.now(UTC)
    if not job.user.is_formal and job.user.trial_successes_remaining > 0:
        job.user.trial_successes_remaining -= 1
    db.commit()
    db.refresh(job)
    return job


def fail_job(db: Session, job: CrawlJob, code: str, message: str) -> CrawlJob:
    job.status = "failed"
    job.error_code = code
    job.error_message = message[:500]
    job.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job
