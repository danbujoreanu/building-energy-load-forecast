---
title: "PartnerRe — Senior AI Architect"
document_type: job_spec
tier: career
company: PartnerRe
role_title: Senior AI Architect
location: Dublin (hybrid assumed) / Luxembourg
source_url: "https://www.linkedin.com/jobs/"
date_added: "2026-04-18"
status: active
application_status: evaluating
tech_stack: ["Snowflake", "Azure", "LangChain", "Semantic Kernel", "Python", "SQL", "MLOps", "Document AI", "Copilot"]
salary_band: unknown
tags: ["ai-architect", "enterprise", "reinsurance", "azure", "snowflake", "llm"]
---

# PartnerRe — Senior AI Architect

**Company:** PartnerRe (privately owned global reinsurer — financial stability focus)  
**Role type:** Hands-on AI Architect — transitioning AI experimentation to enterprise-scale production

---

## What the role does

### Architectural Governance
- Define and enforce where AI workloads run (reference architectures, decision frameworks, guardrails)
- Own architectural decisions for AI workloads enterprise-wide
- Guide engineering teams to implement them

### Delivery & Execution
- Unblock AI pilots and accelerate delivery
- Build reusable MLOps deployment pipelines (resolve resource/capacity bottlenecks)

### Intelligent Integration
- Design "glue" between Snowflake data and Azure applications (robust API standards)
- Implement Document AI: automate entity extraction from policies/claims → downstream systems
- Develop connectors for Microsoft Copilot to securely query internal Snowflake data
- Define secure token/auth/identity patterns
- Establish telemetry and monitoring for all AI workloads
- Optimise model cost/performance: workload placement, caching, throughput tuning

### Stakeholder Engagement
- Partner with business leadership and IT to translate requirements into scalable AI solutions
- Present architectural plans to technical and non-technical audiences
- Evaluate emerging AI technologies

---

## Required Skills

### Technical (explicit)
- Expert in **Snowflake (Cortex, Document AI, Snowpark)** OR **Azure AI Ecosystem (OpenAI, AI Foundry, Azure ML)**
- **Python** (required), SQL
- **LangChain**, Semantic Kernel, or Streamlit
- Vector databases, feature stores
- Orchestration: **Airflow** or **Azure Data Factory**
- LLM evaluation frameworks
- Enterprise architecture tools and methodologies

### Soft Skills
- Strong analytical thinking
- Excellent communication — technical to non-technical
- Player-coach mindset
- Cross-functional collaboration

### Experience
- 7+ years in data engineering, software engineering, or cloud architecture
- Focus on **generative AI**
- Degree in Computer Science, Software Engineering, or equivalent

---

## Fit Analysis vs Dan's Profile

### Strong matches ✅
- Python (expert, 10+ years)
- LLM / RAG architecture (LlamaIndex + ChromaDB + Gemini Flash — Azure equivalents exist)
- MLOps pipeline (drift detection, model versioning, deployment, monitoring)
- FastAPI + Pydantic (enterprise API design patterns)
- Cross-functional stakeholder management (Meta: 10+ teams, VP-level)
- Document AI concepts (intel/ module: PDF/MD ingestion → entity extraction → downstream query)
- Caching and throughput optimisation (Redis TTL cache in predict endpoint)
- Telemetry and monitoring (CloudWatch + drift alerts)
- Communication to non-technical audiences (Meta PM experience, PSPO I)
- 7+ years data/AI/engineering (2015–2026 = 11 years)

### Gaps to address 🔴
- **LangChain**: Not in current Sparc stack (LlamaIndex used instead). Fix: add LangChain portfolio project (1-2 weeks). Framing: "LlamaIndex for document-centric RAG; LangChain familiar with architecture — similar chain/agent patterns."
- **Snowflake**: No production experience. Fix: Snowflake Quickstart + free trial + Azure/Databricks framing ("worked with equivalent columnar warehouse patterns").
- **Semantic Kernel**: Microsoft's LLM orchestration SDK. Less priority — mention awareness.
- **Airflow / Azure Data Factory**: APScheduler used in Sparc (same pattern, different tool). Frame as: "APScheduler for current project; Airflow/ADF for enterprise scale."
- **"AI Architect" title**: Never held this title formally — held Data Science Manager + Senior Program Manager + Product Lead. Reframe Sparc work as "architecting enterprise AI system from scratch."

### Questions to clarify before applying
1. Is this Dublin-based or Luxembourg? (affects commute/relocation decision)
2. Is the team Snowflake-first or Azure-first? (affects preparation priority)
3. What is the current AI maturity — genuinely "transitioning from experimentation" or already in production?

---

## Resume tailoring notes

- Lead with Sparc Energy AI architecture: RAG pipeline, MLOps, FastAPI, LightGBM, drift monitoring
- Map each tech: LlamaIndex ↔ Azure AI Search equivalent; Gemini Flash ↔ Azure OpenAI; ChromaDB ↔ Azure Cognitive Search
- Highlight Document AI: intel/ module (PDF/MD → entity extraction → RAG query → downstream answer synthesis)
- Highlight Meta cross-functional: Engineering + Design + Legal + Marketing + Support + GTM → translates directly to "stakeholder engagement"
- Mention LangChain as planned addition with timeline
- Frame Snowflake gap: "Azure ML / Databricks equivalent patterns; Snowflake architecture review completed"

---

## Technology evaluation for Sparc Energy

Based on this job spec, technologies worth adding to Sparc Energy:

| Technology | Priority | Justification |
|-----------|---------|---------------|
| LangChain (portfolio project) | HIGH | Appears in 60%+ of AI Architect job specs; builds job market visibility |
| Airflow or Prefect | MEDIUM | APScheduler is fine for Sparc; Airflow adds portfolio credibility for enterprise roles |
| Snowflake | LOW | Expensive for Sparc's scale; not needed until B2B commercial data product |
| Semantic Kernel | LOW | Microsoft-specific; not worth adding to Sparc unless Azure-first pivot |
| Azure AI Search | LOW | LlamaIndex + ChromaDB is equivalent and open-source |
