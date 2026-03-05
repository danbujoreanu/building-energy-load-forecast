#!/usr/bin/env python
"""
analyze_building_types.py
=========================
A small analytics script that joins per_building_metrics.csv with metadata.parquet 
to output average MAE/RMSE grouped by building_category. This is crucial for proving
generalization and climate/building transferability (e.g. transfer-learning from
Drammen Schools to Oslo Schools).
"""

import logging
from pathlib import Path
import pandas as pd

# Calculate project root for CWD independence
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

def main():
    metrics_path = PROJECT_ROOT / "outputs/results/per_building_metrics.csv"
    metadata_path = PROJECT_ROOT / "data/processed/metadata.parquet"
    
    if not metrics_path.exists():
        logger.error(f"Metrics not found: {metrics_path}")
        return
        
    if not metadata_path.exists():
        logger.error(f"Metadata not found: {metadata_path}")
        return
        
    logger.info("Loading per-building metrics and metadata...")
    df_metrics = pd.read_csv(metrics_path)
    df_metadata = pd.read_parquet(metadata_path)
    
    # Check if building_id is a column or index in metadata
    if 'building_id' not in df_metadata.columns:
        df_metadata = df_metadata.reset_index()
    
    # Ensure building_id is the same type for joining
    df_metrics['building_id'] = df_metrics['building_id'].astype(str)
    df_metadata['building_id'] = df_metadata['building_id'].astype(str)
    
    logger.info("Joining datasets...")
    # Join the datasets
    df_joined = pd.merge(df_metrics, df_metadata[['building_id', 'building_category']], on='building_id', how='left')
    
    # Group by model and category, calculate mean MAE/RMSE
    logger.info("Calculating category-level metrics...")
    grouped = df_joined.groupby(['model', 'building_category'])[['MAE', 'RMSE', 'MAPE', 'R2']].mean().reset_index()
    
    # Sort for readability (by model, then MAE)
    grouped = grouped.sort_values(by=['model', 'MAE'])
    
    # Display the results
    logger.info("\n" + "="*80 + "\n--- Category-Level Metrics (Average) ---\n" + "="*80)
    for model_name, grp in grouped.groupby('model'):
        logger.info(f"\nModel: {model_name}")
        for _, row in grp.iterrows():
            logger.info(f"  {row['building_category']:>20}: MAE = {row['MAE']:.3f} | RMSE = {row['RMSE']:.3f} | R2 = {row['R2']:.3f}")
            
    # Save the output
    out_path = PROJECT_ROOT / "outputs/results/category_level_metrics.csv"
    grouped.to_csv(out_path, index=False)
    logger.info("=" * 80)
    logger.info(f"Category-level metrics saved to: {out_path.name}")

if __name__ == "__main__":
    main()
