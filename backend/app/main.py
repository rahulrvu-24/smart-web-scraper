from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(
    title="Smart Web Scraper API",
    version="0.1.0",
    description="Turns any webpage into structured JSON using LLM-based extraction.",
)

app.include_router(health_router)