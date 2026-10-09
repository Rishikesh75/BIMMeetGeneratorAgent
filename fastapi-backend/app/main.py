import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers.doc import router as doc_router
from app.routers.ifc import router as ifc_router
from app.routers.plan import router as plan_router
from app.services.bim_llm import bim_llm

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        bim_llm.load()
    except Exception:
        logger.exception("BIM model failed to load; /health will report the error")
    yield


app = FastAPI(title="BIMMeet Generator API", version="1.0.0", lifespan=lifespan)
app.include_router(ifc_router)
app.include_router(plan_router)
app.include_router(doc_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to BIMMeet Generator API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return bim_llm.status()
