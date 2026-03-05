import logging
import pandas as pd
import numpy as np
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

def impute_missing_weather(df: pd.DataFrame, weather_cols: list[str]) -> pd.DataFrame:
    """
    Impute missing weather data (especially Solar Radiation) using MICE (IterativeImputer).
    Takes a MultiIndex DataFrame (building_id, timestamp).
    """
    cols_to_impute = [c for c in weather_cols if c in df.columns]
    if not cols_to_impute:
        return df

    missing_counts = df[cols_to_impute].isna().sum()
    if missing_counts.sum() == 0:
        return df

    logger.info("Missing weather data before MICE:\n%s", missing_counts[missing_counts > 0])

    # For imputation, we use time-based features and temperature to help predict missing Solar/Wind
    # Extract time features if not already present
    ts = df.index.get_level_values("timestamp")
    temp_df = df[cols_to_impute].copy()
    temp_df["hour_of_day"] = ts.hour
    temp_df["month"] = ts.month
    
    # We want to fit MICE. Since IterativeImputer scales based on variance, scaling first is helpful.
    # However, to be fast and avoid leakage, we do a single global imputation on the entire continuous sequence,
    # or per building. Given it's weather, global is fine (climate is the same across buildings).
    
    logger.info("Applying MICE (IterativeImputer) to weather columns...")
    
    imputer = IterativeImputer(
        max_iter=10,
        random_state=42,
        initial_strategy="median",
        skip_complete=True
    )
    
    # Fit and transform
    imputed_values = imputer.fit_transform(temp_df)
    
    # Convert back to DataFrame
    imputed_df = pd.DataFrame(
        imputed_values,
        index=temp_df.index,
        columns=temp_df.columns
    )
    
    # Put back the imputed columns into original df
    df_out = df.copy()
    for col in cols_to_impute:
        # Prevent impossible values (e.g., negative wind or solar)
        if col in ["Global_Solar_Horizontal_Radiation_W_m2", "Wind_Speed_m_s"]:
            imputed_df[col] = imputed_df[col].clip(lower=0)
        df_out[col] = imputed_df[col]

    missing_after = df_out[cols_to_impute].isna().sum()
    logger.info("Missing weather data after MICE:\n%s", missing_after)
    return df_out

def impute_missing_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """
    Impute missing categorical/static features (like energy_label).
    Deep Learning sequence models (like PatchTST) crash if static exog variables have NaNs.
    """
    df_out = df.copy()
    
    if "energy_label" in df_out.columns:
        # Fill missing energy labels with "Unknown" or a dedicated category
        missing_mask = df_out["energy_label"].isna()
        if missing_mask.any():
            missing_count = missing_mask.sum()
            logger.info("Filling %d missing 'energy_label' values with 'Unknown'", missing_count)
            df_out["energy_label"] = df_out["energy_label"].fillna("Unknown")
            
    return df_out
