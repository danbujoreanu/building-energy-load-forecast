---
title: "Dan Bujoreanu — Skills & Experience Profile"
document_type: career_profile
tier: career
status: active
last_updated: "2026-04-18"
tags: ["resume", "skills", "experience", "career-profile"]
---

# Dan Bujoreanu — Skills & Experience Profile

**Email:** dan.bujoreanu@gmail.com | **Location:** Maynooth, Co Kildare, Ireland  
**Education:** MSc Artificial Intelligence, NCI Dublin (2026) | BSc Computer Science  
**Certification:** PSPO I (Professional Scrum Product Owner)

---

## Current Role (2023–present)

**Product Lead / AI Architect — Sparc Energy (Founder)**
- Building an AI-powered energy demand forecasting and demand-response platform for Irish residential and commercial buildings
- Tech stack: Python, FastAPI, LightGBM, LlamaIndex, ChromaDB, Gradio, Pydantic, Docker, AWS (S3, Secrets Manager, CloudWatch, ECR, App Runner)
- Built a full MLOps pipeline: data ingestion → feature engineering → model training → inference API → drift monitoring
- LightGBM H+24 load forecast: MAE 4.03 kWh, R² 0.975 on Drammen test set
- RAG (Retrieval-Augmented Generation) system: LlamaIndex + ChromaDB + sentence-transformers (MiniLM-L6-v2) + Gemini Flash synthesis
- Demand-response control engine: ControlEngine with per-hour DEFER/IDEAL decisions
- FastAPI REST API: /predict (LightGBM inference), /control (demand-response schedule), /intel/* (RAG corpus query)
- Responsible AI: drift detection, model review gates, safety filters on LLM output, GDPR-compliant design

---

## Previous Experience

### Senior Program Manager — Meta (2020–2023)
- Managed cross-functional AI/data science programs across 10+ engineering teams
- Led program management for Ads Delivery AI system improvements (reach, frequency, budget pacing)
- Facilitated Design team collaboration on advertiser UX (Reach & Frequency Curve product)
- Stakeholder management: VP-level presentations, cross-org alignment across Engineering, Product, Legal, Marketing, Measurement, Go-to-Market, and Support
- Shipped ML-powered features: budget pacing improvements, reach and frequency forecasting, delivery system optimisation
- Applied Agile/Scrum at scale: sprint planning, retrospectives, backlog management, OKR alignment

### Data Science Manager — Meta (2020–2021)
- Managed a team of data scientists working on Ads Delivery measurement
- Defined success metrics for ML model launches (incrementality, A/B test design, DM significance testing)
- Translated complex statistical results into executive-level narratives

### Product Support Lead / Acting Product Manager — Meta (2015–2020)
- Acting PM for Ads Delivery tools used by advertisers globally
- Shipped Reach & Frequency Curve: a key advertiser planning tool (cross-functional: Eng, Design, Research, Legal, Marketing)
- Product owner for several Ads Manager features: estimated reach, budget recommendation, delivery diagnostics
- Deepest Design team collaboration experience: participated in 15+ design reviews, co-defined UX principles for advertiser-facing tools
- Managed escalations from Fortune 500 advertiser accounts

---

## Technical Skills

### Machine Learning & AI
- **Gradient boosting:** LightGBM, XGBoost (expert) — H+24 forecasting, tabular ML
- **Deep learning:** PyTorch, TFT (Temporal Fusion Transformer), PatchTST, LSTM (intermediate)
- **Statistics:** Wilcoxon signed-rank, Diebold-Mariano significance testing, conformal prediction
- **MLOps:** model versioning, drift detection, shadow deployment, A/B testing
- **Responsible AI:** output safety filters, human review gates, GDPR compliance design

### LLM / RAG / Agentic AI
- **LlamaIndex** (0.12.x): VectorStoreIndex, SentenceSplitter, HuggingFaceEmbedding, ChromaDB integration
- **ChromaDB** (0.6.3): persistent vector store, metadata filtering, SHA-256 deduplication
- **Embedding models:** sentence-transformers/all-MiniLM-L6-v2 (local), text-embedding-3-small (Azure/OpenAI equivalent)
- **LLM synthesis:** Gemini Flash API (production), Claude claude-haiku-4-5 (agentic tools), GPT-4o (Azure equivalent)
- **Anthropic SDK:** tool-use (function calling), agentic patterns
- **Azure AI equivalents:** Azure AI Search ↔ LlamaIndex+ChromaDB; Azure OpenAI ↔ Gemini; AI Foundry ↔ RAG pipeline
- **Note on LangChain:** Familiar with concepts and architecture; LlamaIndex used for this project (document-centric RAG); LangChain portfolio project planned

### Backend / APIs
- **FastAPI** (expert): async, Pydantic validation, lifespan context managers, APIRouter
- **Python** (expert): 10+ years, scientific stack (numpy, pandas, scikit-learn)
- **SQL**: PostgreSQL, Supabase
- **Redis**: caching, TTL patterns

### Cloud / Infrastructure
- **AWS**: ECR, App Runner, S3, Secrets Manager, CloudWatch, SNS (working knowledge)
- **Azure equivalents**: Container Apps ↔ App Runner; Azure AI Search; Azure Key Vault; Entra ID
- **Docker**: Dockerfile, Docker Compose, multi-stage builds
- **Cloudflare**: Tunnel, Access (Google OAuth gate), CDN

### Data Engineering
- **Snowflake** (Azure/Databricks equivalent): familiar with concepts; not production experience
- **Data pipelines**: APScheduler, pandas ETL, LightGBM feature engineering (35 temporal features)
- **Time-series**: lag features, calendar features, rolling statistics, train/val/test splits with gap

### Product / PM
- PSPO I certified (Professional Scrum Product Owner)
- Linear (project management), Jira equivalent experience
- Product vision, balanced scorecard, OKR frameworks
- Cross-functional: Engineering + Design + Legal + Marketing + Support + GTM

---

## Key Projects

### Sparc Energy — Building Energy Load Forecast
- GitHub: github.com/danbujoreanu/building-energy-load-forecast
- Live demo: energy.danbujoreanu.com (24h demand-response demo)
- Results: LightGBM MAE 4.03 kWh (H+24), R² 0.975, DM test vs PatchTST p<0.001
- Thesis: MSc AI, NCI Dublin 2026 — "Paradigm Parity: Tree Models vs Deep Learning for Building Energy Forecasting"

### Reach & Frequency Curve (Meta, 2017–2019)
- Core advertiser planning tool: shows estimated reach vs frequency for a given budget
- PM role: requirements → design → engineering → launch → measurement
- Users: 500k+ advertisers, including all Fortune 500 Meta advertisers

---

## Languages

- English (native/fluent), Romanian (native), French (working proficiency)

---

## Currently Seeking

- Senior AI/ML roles with product ownership component
- AI Architect / Solutions Architect roles (enterprise AI, LLM, MLOps)
- Senior PM / Product Owner roles in AI/data products
- Open to: Dublin, Remote (EU), hybrid
- Target companies: enterprise tech, energy/sustainability, financial services, reinsurance/insurance
