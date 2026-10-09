"""FastAPI entry point for Lenny Growth Assistant."""

from fastapi import FastAPI

from app.config import get_settings

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
