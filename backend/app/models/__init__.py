# Import every model here so Base.metadata knows about all tables.
# Alembic reads Base.metadata from this package to generate migrations.
from app.db.base import Base
from app.models.user import User

__all__ = ["Base", "User"]