import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd

# We use lightweight dependencies for deployment
import lightgbm as lgb
import joblib

logger = logging.getLogger("uvicorn.error")

# Global model cache to avoid reloading on every request
models = {}

class PredictionRequest(BaseModel):
    building_id: str
    timestamp: str 
    features: dict  # Expecting the 35 engineered features

class PredictionResponse(BaseModel):
    building_id: str
    timestamp: str
    horizon: int
    predictions: list[float]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load Models on Startup
    logger.info("Loading Machine Learning models into memory...")
    try:
        models_dir = Path("outputs/models")
        
        # Searching for LightGBM and Stacking configurations (Mock paths if not present)
        # Assuming format: {city}_{model}_{date}.pkl/.joblib
        lgbm_path = next(models_dir.glob("*_LightGBM_*.joblib"), None)
        stacking_path = next(models_dir.glob("*_Stacking_Ensemble_*.joblib"), None)
        
        if lgbm_path and lgbm_path.exists():
            models["LightGBM"] = joblib.load(lgbm_path)
            logger.info(f"Loaded LightGBM from {lgbm_path}")
        else:
            logger.warning("LightGBM model not found in outputs/models/. Inference will be mocked.")
            models["LightGBM"] = "MOCK_LGBM"
            
        if stacking_path and stacking_path.exists():
            models["Stacking_Ensemble"] = joblib.load(stacking_path)
            logger.info(f"Loaded Stacking Ensemble from {stacking_path}")
        else:
            logger.warning("Stacking Ensemble model not found in outputs/models/. Inference will be mocked.")
            models["Stacking_Ensemble"] = "MOCK_STACKING"
            
    except Exception as e:
        logger.error(f"Failed to load models during startup: {e}")
        
    yield  # Application runs
    
    # Cleanup on Shutdown
    logger.info("Shutting down model inference service...")
    models.clear()

app = FastAPI(
    title="Building Energy Load Forecast API",
    description="Real-time and Day-Ahead inference API for Norwegian Public Buildings.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "models_loaded": list(models.keys())
    }

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, model_name: str = "LightGBM"):
    if model_name not in models:
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not loaded.")
        
    model = models[model_name]
    
    # Convert incoming feature dictionary into a DataFrame for inference
    try:
        # Wrap the dict in a list to create a one-row DataFrame
        df_features = pd.DataFrame([request.features])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid feature format: {e}")
        
    # Execute Model Inference
    try:
        if isinstance(model, str) and model.startswith("MOCK"):
            logger.info(f"Using mocked inference for {model_name}")
            # Mocking a 24-hour H+24 prediction array
            preds = [150.0 + i for i in range(24)]
        else:
            # MultiOutputRegressor or native model wrapped in SKLearn API
            preds = model.predict(df_features)[0].tolist()
            
        # Optional: LightGBM native format might require slightly different invocation if not wrapped
        
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail="Model inference failed.")

    return PredictionResponse(
        building_id=request.building_id,
        timestamp=request.timestamp,
        horizon=len(preds),
        predictions=preds
    )
