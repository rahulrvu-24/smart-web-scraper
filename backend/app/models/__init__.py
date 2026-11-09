# Import every model here so Base.metadata knows about all tables.
# Alembic reads Base.metadata from this package to generate migrations.
from app.db.base import Base
from app.models.api_key import APIKey
from app.models.extraction_schema import ExtractionSchema
from app.models.scrape_job import JobStatus, ScrapeJob
from app.models.scrape_result import ScrapeResult
from app.models.user import User

__all__ = ["Base", "User", "APIKey", "ExtractionSchema", "JobStatus", "ScrapeJob", "ScrapeResult"]