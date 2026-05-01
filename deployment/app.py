import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import asyncpg
import joblib
import lightgbm as lgb  # noqa: F401 — imported to verify lightweight dep
from fastapi import FastAPI

# ── Path setup (src/ package available inside the container) ──────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from energy_forecast.api import schemas as _feature_schemas
from energy_forecast.control.controller import ControlEngine
from deployment.scheduler import create_scheduler, _run_scheduled_inference
from deployment.routers.health import router as health_router
from deployment.routers.meters import router as meters_router
from deployment.routers.control import router as control_router

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — load models + DB pool + scheduler on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 1. Load ML models ────────────────────────────────────────────────────
    logger.info("Loading Machine Learning models into memory...")
    app.state.models = {}
    try:
        models_dir = _REPO_ROOT / "outputs" / "models"

        lgbm_path = next(models_dir.glob("*_LightGBM_*.joblib"), None)
        stacking_path = next(models_dir.glob("*_Stacking_Ensemble_*.joblib"), None)

        if lgbm_path and lgbm_path.exists():
            app.state.models["LightGBM"] = joblib.load(lgbm_path)
            logger.info("Loaded LightGBM from %s", lgbm_path)
            feature_names = getattr(app.state.models["LightGBM"], "feature_name_", None)
            if feature_names is not None:
                _feature_schemas.register_model_features(feature_names)
        else:
            logger.warning("LightGBM model not found in outputs/models/. Inference will be mocked.")
            app.state.models["LightGBM"] = "MOCK_LGBM"

        if stacking_path and stacking_path.exists():
            app.state.models["Stacking_Ensemble"] = joblib.load(stacking_path)
            logger.info("Loaded Stacking Ensemble from %s", stacking_path)
        else:
            logger.warning("Stacking Ensemble not found. Inference will be mocked.")
            app.state.models["Stacking_Ensemble"] = "MOCK_STACKING"

    except Exception as exc:
        logger.error("Failed to load models during startup: %s", exc)

    # ── 2. ControlEngine (stateless — safe to share) ─────────────────────────
    app.state.control_engine = ControlEngine()

    # ── 3. Async DB pool (asyncpg) ───────────────────────────────────────────
    db_url = os.environ.get("DATABASE_URL", "")
    db_pool = None
    if db_url:
        try:
            db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
            app.state.db_pool = db_pool
            logger.info("asyncpg pool connected to %s", db_url.split("@")[-1])
        except Exception as exc:
            logger.warning("Could not connect asyncpg pool: %s — DB endpoints will return 503.", exc)
            app.state.db_pool = None
    else:
        app.state.db_pool = None
        logger.warning("DATABASE_URL not set — DB endpoints disabled.")

    # ── 4. Startup catchup — run inference if 16:00 job was missed today ────
    # Fires once on container start. If it's past 16:00 Dublin and no
    # prediction is stored for today, runs inference immediately so the user
    # doesn't wait until tomorrow after a laptop restart.
    if db_pool:
        try:
            import pytz as _pytz
            _dublin = _pytz.timezone("Europe/Dublin")
            _now_dublin = datetime.now(_dublin)
            if _now_dublin.hour >= 16:
                async with db_pool.acquire() as _conn:
                    _today_count = await _conn.fetchval(
                        "SELECT COUNT(*) FROM predictions WHERE forecast_date = CURRENT_DATE"
                    )
                if not _today_count:
                    logger.info("[startup_catchup] Past 16:00, no prediction for today — running catchup inference.")
                    asyncio.create_task(_run_scheduled_inference(app))
                else:
                    logger.info("[startup_catchup] Today's predictions already stored (%d rows) — no catchup needed.", _today_count)
        except Exception as _exc:
            logger.warning("[startup_catchup] Catchup check failed: %s", _exc)

    # ── 5. APScheduler ───────────────────────────────────────────────────────
    scheduler = create_scheduler(app)
    scheduler.start()
    logger.info(
        "APScheduler started — gap check 09:00, inference 16:00, advisory 20:00, "
        "myenergi poll 23:30, solar_actuals sync 23:45, "
        "data quality check 23:55, weekly quality report Mon 08:30 Europe/Dublin."
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    if db_pool:
        await db_pool.close()
    logger.info("Shutting down model inference service...")
    app.state.models.clear()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Building Energy Load Forecast API",
    description=(
        "Day-ahead electricity load forecasting and demand-response control "
        "for Norwegian public buildings. H+24 horizon, LightGBM + Stacking Ensemble."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(meters_router)
app.include_router(control_router)

# ── Intel module routes (/intel/query, /intel/status, /intel/tiers) ──────────
try:
    from intel.routes import router as _intel_router  # noqa: E402
    app.include_router(_intel_router)
    logger.info("Intel routes registered at /intel/*")
except ImportError as _intel_err:
    logger.warning("Intel module not available — /intel/* routes disabled: %s", _intel_err)
