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
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements separately to leverage Docker cache
# We recreate a lightweight requirements file ignoring heavy DL frameworks
COPY deployment/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and models
# (In production, models might be downloaded from S3 or a model registry rather than baked)
COPY deployment/app.py ./deployment/
COPY src/ ./src/
COPY config/ ./config/
# We copy outputs/models to bundle the .joblib files. 
COPY outputs/models/ ./outputs/models/

# Expose port for FastAPI
EXPOSE 8000

# Run Uvicorn specifically targeting our deployment app
CMD ["uvicorn", "deployment.app:app", "--host", "0.0.0.0", "--port", "8000"]
