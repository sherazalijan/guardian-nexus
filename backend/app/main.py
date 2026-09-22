from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import GuardianError, guardian_exception_handler
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(debug=settings.debug)

logger = get_logger("guardian-nexus")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    logger.info(
        "Starting %s | environment=%s",
        settings.app_name,
        settings.app_env,
    )

    yield

    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(
    GuardianError,
    guardian_exception_handler,
)

app.include_router(router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return a safe response for unexpected application errors."""
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected internal server error occurred.",
                "details": {},
            }
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Return the backend health status."""
    return {
        "status": "ok",
        "service": "guardian-nexus-backend",
    }
