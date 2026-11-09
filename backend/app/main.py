import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.health import root_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.schemas import router as schemas_router
from app.core.config import get_settings
from app.worker.runner import run_worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the background worker with the API, and stop it cleanly on shutdown."""
    stop = asyncio.Event()
    app.state.worker_task = None
    if settings.worker_enabled:
        app.state.worker_task = asyncio.create_task(run_worker(settings, stop))
    yield
    stop.set()
    if app.state.worker_task is not None:
        with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
            await asyncio.wait_for(app.state.worker_task, timeout=10)


app = FastAPI(
    title="Smart Web Scraper API",
    version="0.2.0",
    description="Turns any webpage into structured JSON using LLM-based extraction.",
    lifespan=lifespan,
)

# The Next.js frontend runs on a different origin, so the browser needs CORS headers
# before it will let the frontend read API responses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root_router)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(schemas_router)
app.include_router(jobs_router)
