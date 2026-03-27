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

GROQ_SEMAPHORE = asyncio.Semaphore(2)  # max 2 concurrent Groq calls
OCR_SEMAPHORE = asyncio.Semaphore(1)

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
    extract_address: bool = Form(False),
    extract_education: bool = Form(False),
    extract_experience: bool = Form(False),
    languages: str = Form("eng,tha"),
    empty_value: str = Form("null"),
    extract_mode: str = Form("concise"),
    model: str = Form("llama-3.3-70b-versatile"),
    api_keys: str = Form("{}"),  # JSON string {"groq":"key","openai":"key",...}
):
    config = ParseConfig(
        extract_name=extract_name,
        extract_position=extract_position,
        extract_phone=extract_phone,
        extract_email=extract_email,
        extract_address=extract_address,
        extract_education=extract_education,
        extract_experience=extract_experience,
        languages=languages.split(","),
        empty_value=empty_value,
        extract_mode=extract_mode,
        model=model,
        api_keys=json.loads(api_keys) if api_keys else {},
    )

    batch_id = queue.new_batch(config)
    jobs = []
    skipped = []

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
        except Exception as e:
            fname = getattr(file, "filename", "unknown") or "unknown"
            print(f"[UPLOAD ERROR] {fname}: {e}")
            skipped.append(fname)

    # Fire off all jobs concurrently in background
    background_tasks.add_task(run_all_jobs, batch_id, jobs)

    return {
        "batch_id": batch_id,
        "jobs": queue.get_batch(batch_id),
        "skipped": skipped,
    }


# ── Background worker: parse pipeline ────────────────────────────────────────

async def run_all_jobs(batch_id: str, jobs: list[tuple]):
    config = queue.get_config(batch_id)
    tasks = [run_single_job(batch_id, job_id, tmp_path, suffix, config)
            for job_id, tmp_path, suffix in jobs]
    await asyncio.gather(*tasks)

    # ── Auto-save to SQLite when batch completes ──
    finished_jobs = queue.get_batch(batch_id)
    if finished_jobs:
        db_save_batch(batch_id, finished_jobs)


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

        async with GROQ_SEMAPHORE:
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
        print(f"[FAIL] {job_id} error: {e}")  # <- For debugging
        import traceback; traceback.print_exc() 
        await queue.update_job(
            batch_id, job_id,
            status=JobStatus.failed,
            error=str(e),
        )
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)                                                                    │                os.unlink(tmp_path) 
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
        text, is_text = await asyncio.to_thread(extract_text_from_pdf,path) 
        if is_text:
            return text, "pdf-text", 0.0
        else:
            # Scanned PDF — run OCR
            async with OCR_SEMAPHORE:
                text, conf = await asyncio.to_thread(ocr_scanned_pdf, path, languages)
            return text, "pdf-ocr", conf

    elif suffix in IMAGE_EXTS:
        async with OCR_SEMAPHORE:
            text, conf = await asyncio.to_thread(ocr_image_file, path, languages)
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
        headers={"Content-Disposition": f"attachment; filename=Extracted_Data{batch_id[:8]}.xlsx"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/models")
async def get_models():
    """Return all available models grouped by provider."""
    from extractors.field_parser import ALL_MODELS, DEFAULT_MODEL
    return {
        "models": ALL_MODELS,
        "default": DEFAULT_MODEL,
    }

# ── Batch History ─────────────────────────────────────────────────────────────

from workers.History_db import list_batches, get_batch_jobs, delete_batch, save_batch as db_save_batch

@app.get("/api/history")
async def get_history():
    """List all saved batches."""
    return {"batches": list_batches()}

@app.get("/api/history/{batch_id}/export")
async def export_history_excel(batch_id: str):
    """Re-export Excel for a historical batch from SQLite."""
    rows = get_batch_jobs(batch_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Batch not found in history")

    # Reconstruct ParseJob objects from DB rows
    jobs = []
    for r in rows:
        from api.models import ParseJob
        job = ParseJob(
            job_id=r["job_id"],
            filename=r["filename"],
            status=JobStatus(r["status"]),
            parse_method=r["parse_method"] or "",
            file_size_kb=r["file_size_kb"] or 0,
            error=r["error"],
            result=ExtractedFields(
                name=r["name"],
                name_cert=r.get("name_cert") or "absent",
                position=r["position"],
                position_cert=r.get("position_cert") or "absent",
                phone=r["phone"],
                email=r["email"],
                confidence=r["confidence"] or 0,
            ) if r["status"] in ("done", "low_confidence") else None,
        )
        jobs.append(job)

    xlsx_bytes = build_excel(jobs)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=history_{batch_id[:8]}.xlsx"},
    ) 

@app.delete("/api/history/{batch_id}")
async def delete_history_batch(batch_id: str):
    delete_batch(batch_id)
    return {"deleted": batch_id}