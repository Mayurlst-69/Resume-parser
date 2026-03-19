from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"
    low_confidence = "low_confidence"


class ExtractedFields(BaseModel):
    name: Optional[str] = None
    name_cert: str = "absent"        # confident | unsure | absent
    position: Optional[str] = None
    position_cert: str = "absent"    # confident | unsure | absent
    phone: Optional[str] = None
    email: Optional[str] = None
    confidence: float = 0.0


class ParseJob(BaseModel):
    job_id: str
    filename: str
    status: JobStatus = JobStatus.queued
    file_size_kb: float = 0.0
    parse_method: str = ""
    result: Optional[ExtractedFields] = None
    error: Optional[str] = None


class ParseConfig(BaseModel):
    extract_name: bool = True
    extract_position: bool = True
    extract_phone: bool = True
    extract_email: bool = True
    languages: List[str] = ["eng", "tha"]
    empty_value: str = "null"  # "null" or ""
    extract_mode: str = "concise"  # "concise" | "general"


class BatchParseResponse(BaseModel):
    batch_id: str
    jobs: List[ParseJob]


class ExportRequest(BaseModel):
    batch_id: str