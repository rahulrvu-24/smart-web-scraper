from fastapi import FastAPI

app = FastAPI(
    title="Smart Web Scraper API",
    version="0.1.0",
    description="Turns any webpage into structured JSON using LLM-based extraction.",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness check: the API process is up and answering requests."""
    return {"status": "ok"}