from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api_gateway.routers import posts
from core.config import backend_mode, settings
from core.huggingface_client import hf_client

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:
    Instrumentator = None


app = FastAPI(
    title="AI Social Media Post Generator API",
    description="Generate marketing prompts, captions, hashtags, and images.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts.router)
app.mount("/static", StaticFiles(directory=settings.outputs_dir), name="static")

if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str | dict[str, str]]:
    from core.config import get_hf_api_key
    return {
        "status": "ok",
        "mode": backend_mode(),
        "hf_configured": "yes" if get_hf_api_key() else "no",
        "hf": hf_client.diagnostics(),
    }


@app.get("/diagnostics/huggingface", tags=["Health"])
async def huggingface_diagnostics() -> dict[str, str]:
    return hf_client.diagnostics()