from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.models.job import CrawlJob
from backend.app.models.user import User
from backend.app.models.profile import CredentialProfile, ProxyProfile
from backend.app.core.config import get_settings
from backend.app.core.crypto import decrypt_secret
from backend.app.services.crawlers import REGISTRY


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


def execute_job(db: Session, job_id: int) -> CrawlJob:
    job = db.get(CrawlJob, job_id)
    if not job:
        raise ValueError("JOB_NOT_FOUND")
    job.status = "running"
    db.commit()
    try:
        credential = db.get(CredentialProfile, job.credential_profile_id) if job.credential_profile_id else None
        proxy = db.get(ProxyProfile, job.proxy_profile_id) if job.proxy_profile_id else None
        if credential and credential.user_id != job.user_id:
            raise ValueError("CREDENTIAL_PROFILE_NOT_FOUND")
        if proxy and proxy.user_id != job.user_id:
            raise ValueError("PROXY_PROFILE_NOT_FOUND")
        key = get_settings().credential_encryption_key
        cookie = decrypt_secret(credential.cookie_ciphertext, key) if credential else None
        proxy_url = None
        if proxy:
            username = decrypt_secret(proxy.username_ciphertext, key) if proxy.username_ciphertext else None
            password = decrypt_secret(proxy.password_ciphertext, key) if proxy.password_ciphertext else None
            auth = f"{username}:{password}@" if username and password else ""
            proxy_url = f"{proxy.protocol}://{auth}{proxy.host}:{proxy.port}"
        result = REGISTRY[job.crawler](job.input, cookie, proxy_url)
        return complete_job(db, job, result)
    except ValueError as exc:
        return fail_job(db, job, str(exc), "Crawler request could not be completed")
    except Exception:
        return fail_job(db, job, "CRAWLER_FAILED", "Crawler execution failed")
