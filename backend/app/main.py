from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.config import get_settings
from app.logging_config import configure_logging
from app.rate_limiter import limiter

configure_logging()

settings = get_settings()
app = FastAPI(
    title="Outil de trésorerie",
    description="API de l'outil de gestion de trésorerie auto-hébergé",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "name": "tresorerie-backend"}
