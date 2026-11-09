from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.schemas import router as schemas_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Smart Web Scraper API",
    version="0.1.0",
    description="Turns any webpage into structured JSON using LLM-based extraction.",
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

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(schemas_router)
