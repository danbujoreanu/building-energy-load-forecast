# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Set working directory
WORKDIR /app

# Install system dependencies (required for lightgbm compilation if no binary exists)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Health check — App Runner and ECS both use this
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Copy the requirements separately to leverage Docker cache
# We recreate a lightweight requirements file ignoring heavy DL frameworks
COPY deployment/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY deployment/__init__.py ./deployment/
COPY deployment/app.py ./deployment/
COPY deployment/connectors.py ./deployment/
COPY deployment/live_inference.py ./deployment/
COPY src/ ./src/
COPY config/ ./config/

# Copy inference models — RandomForest files (~400MB each) are excluded via .dockerignore
# What arrives here: LightGBM (~2.8MB), XGBoost (~2.3MB), Ridge (~4KB) per city = ~11MB total
COPY outputs/models/ ./outputs/models/

# Expose port for FastAPI
EXPOSE 8000

# Run Uvicorn specifically targeting our deployment app
CMD ["uvicorn", "deployment.app:app", "--host", "0.0.0.0", "--port", "8000"]
