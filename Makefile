# ────────────────────────────────────────────────────────────────────────────
# Building Energy Load Forecast — Makefile
# Usage: make <target>
# ────────────────────────────────────────────────────────────────────────────

PYTHON      := /Users/danalexandrubujoreanu/miniconda3/envs/ml_lab1/bin/python
IMAGE_NAME  := energy-forecast-api
IMAGE_TAG   := latest
ECR_REPO    ?= $(AWS_ACCOUNT_ID).dkr.ecr.eu-west-1.amazonaws.com/$(IMAGE_NAME)
PORT        := 8000

.PHONY: help install test lint train docker-build docker-run docker-stop \
        ecr-login ecr-push apprunner-deploy live-demo sprint3

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo "Building Energy Load Forecast"
	@echo ""
	@echo "Research pipeline:"
	@echo "  make train          Run full Drammen pipeline (LightGBM/XGBoost/Ridge/Stacking)"
	@echo "  make sweep          Run horizon sweep H+1/6/12/24/48"
	@echo "  make sprint3        Run Oslo full paradigm parity (Setup A + C)"
	@echo "  make significance   Run Wilcoxon + DM significance tests"
	@echo ""
	@echo "Deployment:"
	@echo "  make docker-build   Build Docker image locally"
	@echo "  make docker-run     Run container locally on port $(PORT)"
	@echo "  make docker-stop    Stop running container"
	@echo "  make live-demo      Run morning brief CLI (dry-run, no Docker)"
	@echo ""
	@echo "AWS:"
	@echo "  make ecr-login      Authenticate Docker with ECR (eu-west-1)"
	@echo "  make ecr-push       Build + push to ECR (requires AWS_ACCOUNT_ID env var)"
	@echo "  make apprunner-deploy  Deploy to AWS App Runner (requires apprunner service ARN)"
	@echo ""
	@echo "Dev:"
	@echo "  make install        Install package in editable mode"
	@echo "  make test           Run test suite"
	@echo "  make lint           Run ruff linter"

# ── Research Pipeline ─────────────────────────────────────────────────────────
install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/ scripts/ deployment/

train:
	$(PYTHON) scripts/run_pipeline.py --save-predictions

sweep:
	$(PYTHON) scripts/run_horizon_sweep.py --resume

sweep-dl:
	$(PYTHON) scripts/run_horizon_sweep.py --include-dl --resume

sprint3:
	@echo "Running Oslo full paradigm parity (Setup A + Setup C)..."
	$(PYTHON) scripts/run_pipeline.py --city oslo --save-predictions
	$(PYTHON) scripts/run_raw_dl.py --city oslo --save-predictions

significance:
	$(PYTHON) scripts/significance_test.py

# ── Local Deployment ──────────────────────────────────────────────────────────
live-demo:
	$(PYTHON) deployment/live_inference.py --dry-run

docker-build:
	docker build -f deployment/Dockerfile -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo "Built $(IMAGE_NAME):$(IMAGE_TAG)"
	@echo "Image size: $$(docker image inspect $(IMAGE_NAME):$(IMAGE_TAG) --format='{{.Size}}' | awk '{printf \"%.0f MB\", $$1/1024/1024}')"

docker-run:
	docker run -d \
	  --name $(IMAGE_NAME) \
	  -p $(PORT):8000 \
	  -v $$(pwd)/outputs/models:/app/outputs/models \
	  -e LOG_LEVEL=INFO \
	  $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "API running at http://localhost:$(PORT)"
	@echo "Health: http://localhost:$(PORT)/health"
	@echo "Docs:   http://localhost:$(PORT)/docs"

docker-stop:
	docker stop $(IMAGE_NAME) && docker rm $(IMAGE_NAME) || true

docker-logs:
	docker logs -f $(IMAGE_NAME)

# Test the running container
docker-test:
	curl -s http://localhost:$(PORT)/health | python3 -m json.tool
	@echo ""
	curl -s -X POST http://localhost:$(PORT)/control \
	  -H "Content-Type: application/json" \
	  -d '{"building_id":"B001","city":"drammen","dry_run":true}' | python3 -m json.tool

# ── AWS ECR + App Runner ──────────────────────────────────────────────────────
ecr-login:
	aws ecr get-login-password --region eu-west-1 | \
	  docker login --username AWS --password-stdin $(ECR_REPO)

ecr-push: docker-build ecr-login
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(ECR_REPO):$(IMAGE_TAG)
	docker push $(ECR_REPO):$(IMAGE_TAG)
	@echo "Pushed to ECR: $(ECR_REPO):$(IMAGE_TAG)"

# Create ECR repo (run once)
ecr-create-repo:
	aws ecr create-repository \
	  --repository-name $(IMAGE_NAME) \
	  --region eu-west-1 \
	  --image-scanning-configuration scanOnPush=true

# Deploy to App Runner (update existing service — requires SERVICE_ARN env var)
apprunner-deploy:
	@test -n "$(SERVICE_ARN)" || (echo "Set SERVICE_ARN env var first" && exit 1)
	aws apprunner start-deployment --service-arn $(SERVICE_ARN) --region eu-west-1
	@echo "Deployment triggered. Monitor at:"
	@echo "  https://eu-west-1.console.aws.amazon.com/apprunner/"
