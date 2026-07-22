from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.deps import current_user
from backend.app.db.session import get_db
from backend.app.models.job import CrawlJob
from backend.app.models.user import User
from backend.app.schemas.jobs import JobResponse, JobResultResponse


router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def owned_job(job_id: int, db: Session, user: User) -> CrawlJob:
    job = db.get(CrawlJob, job_id)
    if not job or (job.user_id != user.id and not user.is_admin):
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> CrawlJob:
    return owned_job(job_id, db, user)


@router.get("/{job_id}/result", response_model=JobResultResponse)
def get_job_result(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> JobResultResponse:
    job = owned_job(job_id, db, user)
    if job.status != "succeeded" or job.result is None:
        raise HTTPException(status_code=409, detail="JOB_NOT_COMPLETE")
    return JobResultResponse(id=job.id, status=job.status, result=job.result)
