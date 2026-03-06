#!/bin/bash
echo "Starting Oslo Pipeline run... Logging to outputs/logs/run_oslo_generalization.log"
mkdir -p outputs/logs
/Users/danalexandrubujoreanu/miniconda3/envs/ml_lab1/bin/python scripts/run_pipeline.py --city oslo --skip-slow --stages training > outputs/logs/run_oslo_generalization.log 2>&1 &
echo "Started. You can view the log by opening outputs/logs/run_oslo_generalization.log"
