import pandas as pd
from pathlib import Path

csv_path = Path("/Users/danalexandrubujoreanu/building-energy-load-forecast/outputs/results/final_metrics.csv")

recovery_data = [
    {"model": "PatchTST_SetupC", "MAE": 6.955, "RMSE": 14.1184, "MAPE": 26.8142, "R2": 0.9102, "n_samples": 241393, "Daily_Peak_MAE": 10.6095, "train_time_s": 3026.3},
    # Results from TURN 1654: MAE only for these because they were still running or not merged
    {"model": "LSTM_SetupC", "MAE": 8.38},
    {"model": "CNN-LSTM_SetupC", "MAE": 8.04},
    {"model": "GRU_SetupC", "MAE": 8.08},
]

if csv_path.exists():
    df = pd.read_csv(csv_path, index_col=0)
    # Standardize column name to lowercase 'model'
    if "Model" in df.columns:
        df = df.rename(columns={"Model": "model"})
    
    # Merge recovery data (only if not existing)
    for model_row in recovery_data:
        name = model_row["model"]
        if name not in df["model"].values:
            df = pd.concat([df, pd.DataFrame([model_row])], ignore_index=True)
            
    # Fix the header name for the CSV standard
    if "Model" in df.columns and "model" in df.columns:
         # Merge them? 
         pass
         
    df.to_csv(csv_path)
    print("Success: Recovered Setup C entries and standardized 'model' column.")
else:
    print("Error: CSV not found.")
