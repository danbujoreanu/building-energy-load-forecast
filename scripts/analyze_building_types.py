import pandas as pd
from pathlib import Path

def main():
    metrics_file = Path("outputs/results/per_building_metrics.csv")
    meta_file = Path("data/processed/metadata.parquet")
    
    if not metrics_file.exists():
        print(f"Error: {metrics_file} not found.")
        return
    if not meta_file.exists():
        print(f"Error: {meta_file} not found.")
        return
        
    metrics = pd.read_csv(metrics_file)
    meta = pd.read_parquet(meta_file)
    
    # Assuming building_id might be index in meta, or a column
    if 'building_id' not in meta.columns and meta.index.name in ('building_id', 'id'):
        meta = meta.reset_index()
    elif 'building_id' not in meta.columns:
        # try to rename first column
        meta = meta.reset_index()
        meta.rename(columns={'index': 'building_id'}, inplace=True)
        
    # Standardize column name if needed
    if 'building_id' not in metrics.columns:
        print(f"Columns in metrics: {metrics.columns.tolist()}")
        print(f"Columns in meta: {meta.columns.tolist()}")
        
    df = metrics.merge(meta, on='building_id', how='left')
    
    if 'building_category' not in df.columns:
        print(f"building_category column not found. Available columns: {df.columns.tolist()}")
        return
        
    summary = df.groupby(['building_category', 'model'])[['MAE', 'RMSE', 'R2']].mean().reset_index()
    
    # Sort by building category and then MAE
    summary = summary.sort_values(by=['building_category', 'MAE'])
    
    print("\n" + "="*80)
    print(f"🍎 Category-Level Performance Analytics (Apples-to-Apples)")
    print("="*80)
    print(summary.to_string(index=False))
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
