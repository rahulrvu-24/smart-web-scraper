"""The worker: claim a job, fetch the page, extract with the LLM, save the result."""

import asyncio
import contextlib
import logging
import uuid

from pydantic import ValidationError

from app.core.config import Settings
from app.db.session import SessionLocal
from app.extraction.fields import FieldSet
from app.extraction.llm import LLMError, extract
from app.models import ScrapeResult
from app.scraper.fetcher import FetchError, fetch_page
from app.scraper.html_clean import clean_html
from app.scraper.url_guard import UnsafeURLError
from app.worker import queue

log = logging.getLogger(__name__)


def _in_session(fn, *args):
    with SessionLocal() as db:
        return fn(db, *args)


async def process_job(job: queue.ClaimedJob, settings: Settings) -> None:
    log.info("Job %s attempt %d: %s", job.id, job.attempts, job.url)
    try:
        fields = FieldSet(fields=job.fields).fields
        page = await fetch_page(job.url, settings, render_js=job.render_js)
        clean = await asyncio.to_thread(clean_html, page.html)
        if not clean.text and not clean.json_ld:
            raise FetchError("The page had no readable text")
        extraction = await extract(fields, clean, page.url, settings)
    except ValidationError:
        await _fail(job.id, "The job's field list is invalid", retryable=False, settings=settings)
    except UnsafeURLError as exc:
        await _fail(job.id, f"Blocked: {exc}", retryable=False, settings=settings)
    except LLMError as exc:
        await _record_usage(job, exc.attempts)
        await _fail(job.id, str(exc), retryable=exc.retryable, settings=settings)
    except FetchError as exc:
        await _fail(job.id, str(exc), retryable=exc.retryable, settings=settings)
    except Exception:  # noqa: BLE001 - one bad job must never kill the worker
        log.exception("Job %s crashed", job.id)
        await _fail(job.id, "Internal error while processing the page", retryable=True, settings=settings)
    else:
        result = ScrapeResult(
            data=extraction.data,
            is_valid=extraction.is_valid,
            validation_errors=extraction.errors or None,
            llm_model=extraction.model,
            final_url=page.url,
            page_title=clean.title[:500] or None,
            fetch_method=page.method,
            input_tokens=extraction.input_tokens,
            output_tokens=extraction.output_tokens,
            latency_ms=extraction.latency_ms,
        )
        await _record_usage(job, extraction.attempts)
        await asyncio.to_thread(_in_session, queue.mark_succeeded, job.id, result)
        log.info("Job %s succeeded with %s (valid=%s)", job.id, extraction.model, extraction.is_valid)


async def _record_usage(job: queue.ClaimedJob, attempts: list) -> None:
    try:
        await asyncio.to_thread(_in_session, queue.record_llm_usage, job.user_id, job.id, attempts)
    except Exception:  # noqa: BLE001 - losing a usage row must never fail the job
        log.exception("Could not record LLM usage for job %s", job.id)


async def _fail(job_id: uuid.UUID, message: str, retryable: bool, settings: Settings) -> None:
    log.warning("Job %s failed (retryable=%s): %s", job_id, retryable, message)
    await asyncio.to_thread(_in_session, queue.mark_failed, job_id, message, retryable, settings)


async def run_worker(settings: Settings, stop: asyncio.Event) -> None:
    """Poll for jobs until `stop` is set. Processes one job at a time to keep memory low."""
    log.info("Worker started")
    loops = 0
    while not stop.is_set():
        if loops % 30 == 0:
            with contextlib.suppress(Exception):
                requeued = await asyncio.to_thread(_in_session, queue.recover_stale_jobs, settings)
                if requeued:
                    log.info("Re-queued %d stale jobs", requeued)
        loops += 1
        try:
            job = await asyncio.to_thread(_in_session, queue.claim_next_job)
        except Exception:  # noqa: BLE001 - database blip: wait and try again
            log.exception("Could not claim a job")
            job = None
        if job is None:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=settings.worker_poll_seconds)
            continue
        await process_job(job, settings)
    log.info("Worker stopped")
