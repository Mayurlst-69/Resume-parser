import asyncio
import uuid
from typing import Dict, List, Optional
from api.models import ParseJob, ParseConfig, JobStatus


class JobQueue:
    """
    Simple in-memory async job queue.
    No Redis/Celery needed for Windows dev.
    Each file is an isolated task — one failure never blocks others.
    """

    def __init__(self):
        self._batches: Dict[str, List[ParseJob]] = {}
        self._configs: Dict[str, ParseConfig] = {}
        self._lock = asyncio.Lock()

    def new_batch(self, config: ParseConfig) -> str:
        batch_id = str(uuid.uuid4())
        self._batches[batch_id] = []
        self._configs[batch_id] = config
        return batch_id

    def add_job(self, batch_id: str, filename: str, file_size_kb: float) -> ParseJob:
        job = ParseJob(
            job_id=str(uuid.uuid4()),
            filename=filename,
            file_size_kb=round(file_size_kb, 1),
        )
        self._batches[batch_id].append(job)
        return job

    def get_batch(self, batch_id: str) -> Optional[List[ParseJob]]:
        return self._batches.get(batch_id)

    def get_config(self, batch_id: str) -> Optional[ParseConfig]:
        return self._configs.get(batch_id)

    def get_job(self, batch_id: str, job_id: str) -> Optional[ParseJob]:
        for job in self._batches.get(batch_id, []):
            if job.job_id == job_id:
                return job
        return None

    async def update_job(self, batch_id: str, job_id: str, **kwargs):
        async with self._lock:
            job = self.get_job(batch_id, job_id)
            if job:
                for k, v in kwargs.items():
                    setattr(job, k, v)

    def all_done(self, batch_id: str) -> bool:
        jobs = self._batches.get(batch_id, [])
        return all(
            j.status in (JobStatus.done, JobStatus.failed, JobStatus.low_confidence)
            for j in jobs
        )


# Singleton — shared across the FastAPI app lifetime
queue = JobQueue()
