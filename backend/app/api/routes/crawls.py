from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import current_api_token, current_user
from backend.app.core.rate_limit import enforce_rate_limit
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.jobs import CrawlCreate, JobResponse
from backend.app.services.jobs import create_job
from backend.app.workers.tasks import run_crawl_job
from src.common.models.crawler import CrawlerName


router = APIRouter(prefix="/api/v1/crawls", tags=["crawls"])


@router.post("/{crawler}", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_crawl(
    crawler: CrawlerName,
    payload: CrawlCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    api_token=Depends(current_api_token),
):
    if not user.is_formal and user.trial_successes_remaining <= 0:
        raise HTTPException(status_code=403, detail="TRIAL_QUOTA_EXHAUSTED")
    if api_token:
        enforce_rate_limit(str(api_token.id), user.is_formal)
    job = create_job(db, user, crawler.value, payload.input, payload.credential_profile_id, payload.proxy_profile_id)
    run_crawl_job.delay(job.id)
    return job
