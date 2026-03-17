import os
import uuid
import asyncio
import tempfile
import json
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from dotenv import load_dotenv

load_dotenv()

from api.models import ParseConfig, ParseJob, JobStatus, ExtractedFields
from workers.job_queue import queue
from extractors.pdf_extractor import extract_text_from_pdf
from extractors.ocr_extractor import ocr_image_file, ocr_scanned_pdf
from extractors.field_parser import parse_fields
from exporters.excel_exporter import build_excel

app = FastAPI(title="Resume Parser API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
PDF_EXT = ".pdf"

LOW_CONFIDENCE_THRESHOLD = 0.60


# ── Upload & start batch ──────────────────────────────────────────────────────

@app.post("/api/parse")
async def parse_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    extract_name: bool = Form(True),
    extract_position: bool = Form(True),
    extract_phone: bool = Form(True),
    extract_email: bool = Form(True),
    languages: str = Form("eng,tha"),
    empty_value: str = Form("null"),
):
    config = ParseConfig(
        extract_name=extract_name,
        extract_position=extract_position,
        extract_phone=extract_phone,
        extract_email=extract_email,
        languages=languages.split(","),
        empty_value=empty_value,
    )

    batch_id = queue.new_batch(config)
    jobs = []

    for file in files:
        size_kb = 0.0
        try:
            content = await file.read()
            size_kb = len(content) / 1024
            # Store file temporarily
            suffix = Path(file.filename or "file").suffix.lower()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(content)
            tmp.close()

            job = queue.add_job(batch_id, file.filename or "unknown", size_kb)
            jobs.append((job.job_id, tmp.name, suffix))
        except Exception:
            pass

    # Fire off all jobs concurrently in background
    background_tasks.add_task(run_all_jobs, batch_id, jobs)

    return {
        "batch_id": batch_id,
        "jobs": queue.get_batch(batch_id),
    }


# ── Background worker: parse pipeline ────────────────────────────────────────

async def run_all_jobs(batch_id: str, jobs: list[tuple]):
    config = queue.get_config(batch_id)
    tasks = [run_single_job(batch_id, job_id, tmp_path, suffix, config)
            for job_id, tmp_path, suffix in jobs]
    await asyncio.gather(*tasks)


async def run_single_job(
    batch_id: str,
    job_id: str,
    tmp_path: str,
    suffix: str,
    config: ParseConfig,
):
    await queue.update_job(batch_id, job_id, status=JobStatus.processing)
    try:
        text, method, ocr_conf = await extract_text(tmp_path, suffix, config.languages)

        if not text.strip():
            await queue.update_job(
                batch_id, job_id,
                status=JobStatus.failed,
                error="Could not extract any text",
                parse_method=method,
            )
            return

        fields = await parse_fields(text, config)

        # Blend OCR confidence into final confidence for image-based files
        if ocr_conf > 0:
            fields.confidence = round((fields.confidence + ocr_conf) / 2, 2)

        status = (
            JobStatus.low_confidence
            if fields.confidence < LOW_CONFIDENCE_THRESHOLD
            else JobStatus.done
        )

        await queue.update_job(
            batch_id, job_id,
            status=status,
            result=fields,
            parse_method=method,
        )

    except Exception as e:
        await queue.update_job(
            batch_id, job_id,
            status=JobStatus.failed,
            error=str(e),
        )
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def extract_text(
    path: str, suffix: str, languages: list[str]
) -> tuple[str, str, float]:
    """
    Parser waterfall:
    PDF → try text layer → if empty → OCR
    Image → OCR directly
    Returns (text, method_label, ocr_confidence)
    """
    if suffix == PDF_EXT:
        text, is_text = extract_text_from_pdf(path)
        if is_text:
            return text, "pdf-text", 0.0
        else:
            # Scanned PDF — run OCR
            text, conf = ocr_scanned_pdf(path, languages)
            return text, "pdf-ocr", conf

    elif suffix in IMAGE_EXTS:
        text, conf = ocr_image_file(path, languages)
        return text, "image-ocr", conf

    return "", "unknown", 0.0


# ── SSE: real-time status stream ──────────────────────────────────────────────

@app.get("/api/status/{batch_id}")
async def stream_status(batch_id: str):
    """
    Server-Sent Events endpoint.
    Frontend subscribes and gets live job updates.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        sent_states: dict[str, str] = {}
        while True:
            jobs = queue.get_batch(batch_id)
            if jobs is None:
                yield f"data: {json.dumps({'error': 'batch not found'})}\n\n"
                break

            for job in jobs:
                state_key = f"{job.job_id}:{job.status}"
                if sent_states.get(job.job_id) != state_key:
                    sent_states[job.job_id] = state_key
                    payload = {
                        "job_id": job.job_id,
                        "filename": job.filename,
                        "status": job.status.value,
                        "file_size_kb": job.file_size_kb,
                        "parse_method": job.parse_method,
                        "result": job.result.model_dump() if job.result else None,
                        "error": job.error,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            if queue.all_done(batch_id):
                yield f"data: {json.dumps({'event': 'batch_complete', 'batch_id': batch_id})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Get batch results ─────────────────────────────────────────────────────────

@app.get("/api/batch/{batch_id}")
async def get_batch(batch_id: str):
    jobs = queue.get_batch(batch_id)
    if jobs is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"batch_id": batch_id, "jobs": jobs}


# ── Export Excel ──────────────────────────────────────────────────────────────

@app.get("/api/export/{batch_id}")
async def export_excel(batch_id: str):
    jobs = queue.get_batch(batch_id)
    if jobs is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    config = queue.get_config(batch_id)
    xlsx_bytes = build_excel(jobs, config)

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=resumes_{batch_id[:8]}.xlsx"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
