from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_gateway.routers import posts
from core.config import settings

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:  # pragma: no cover
    Instrumentator = None


app = FastAPI(
    title="AI Social Media Post Generator API",
    description="Generate marketing prompts, captions, hashtags, and images.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts.router)

if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}