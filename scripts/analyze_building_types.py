from pathlib import Path

import pandas as pd


def main():
    cities = ['drammen', 'oslo']
    for city in cities:
        meta_file = Path(f"data/processed/{city}_metadata.parquet")
        if not meta_file.exists():
            print(f"Error: {meta_file} not found. Skipping {city}.")
            continue

        meta = pd.read_parquet(meta_file)

        # Assuming building_id might be index in meta, or a column
        if 'building_id' not in meta.columns and meta.index.name in ('building_id', 'id'):
            meta = meta.reset_index()
        elif 'building_id' not in meta.columns:
            # try to rename first column
            meta = meta.reset_index()
            meta.rename(columns={'index': 'building_id'}, inplace=True)

        metrics_file = Path(f"outputs/results/{city}_per_building_metrics.csv")

        if not metrics_file.exists():
            print(f"Error: {metrics_file} not found for city {city}")
            continue

        metrics = pd.read_csv(metrics_file)

        # Standardize column name if needed
        if 'building_id' not in metrics.columns:
            print(f"Columns in metrics: {metrics.columns.tolist()}")
            continue

        df = metrics.merge(meta, on='building_id', how='left')

        if 'building_category' not in df.columns:
            print(f"building_category column not found. Available columns: {df.columns.tolist()}")
            continue

        summary = df.groupby(['building_category', 'model'])[['MAE', 'RMSE', 'R2']].mean().reset_index()
        summary['city'] = city

        # Sort by building category and then MAE
        summary = summary.sort_values(by=['building_category', 'MAE'])

        out_csv = Path(f"outputs/results/{city}_category_level_metrics.csv")
        summary.to_csv(out_csv, index=False)

        print("\n" + "="*80)
        print(f"🍎 Category-Level Performance Analytics (Apples-to-Apples) for {city.upper()}")
        print("="*80)
        print(summary.to_string(index=False))
        print("="*80 + "\n")

if __name__ == "__main__":
    main()
