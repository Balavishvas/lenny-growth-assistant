"""FastAPI entry point for Lenny Growth Assistant."""

from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import check_database_connection

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Evidence-grounded assistant for product and growth research.",
)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    """Report API process liveness; this does not imply DB/model readiness."""
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}


@app.get("/health/database", tags=["operations"])
def database_health() -> dict[str, str]:
    """Check whether the configured database can execute a simple query."""
    try:
        check_database_connection()
    except SQLAlchemyError:
        # Avoid returning driver details or credentials in the API response.
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check the local DATABASE_URL and PostgreSQL service.",
        ) from None

    return {"status": "ok", "database": "connected"}
