import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.routes import auth, captchas, attacks, experiments, events, backtests, reports, metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CAPTCHA Benchmark API — env=%s", settings.ENVIRONMENT)
    # Pre-warm PAS model on startup
    try:
        from app.ml.pas_model import get_current_model
        model = get_current_model()
        logger.info("PAS model ready: version=%s", model.version)
    except Exception as e:
        logger.warning("PAS model warm-up failed (non-fatal): %s", e)
    yield
    logger.info("Shutting down CAPTCHA Benchmark API")


app = FastAPI(
    title="CAPTCHA Robustness Benchmark Dashboard",
    version="1.0.0",
    description=(
        "Production-grade evaluation platform for CAPTCHA robustness. "
        "Based on Kozlov et al. (RAID 2020) PAS methodology and "
        "Gao et al. (USENIX SEC 2021) attack framework."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8888", "http://localhost:4000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(captchas.router)
app.include_router(attacks.router)
app.include_router(experiments.router)
app.include_router(events.router)
app.include_router(backtests.router)
app.include_router(reports.router)
app.include_router(metrics.router)


@app.get("/healthz")
async def health():
    return {"status": "ok", "version": "1.0.0", "environment": settings.ENVIRONMENT}


@app.get("/")
async def root():
    return JSONResponse({"message": "CAPTCHA Benchmark API", "docs": "/docs"})
