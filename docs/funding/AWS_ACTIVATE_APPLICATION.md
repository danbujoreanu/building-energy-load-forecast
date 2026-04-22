# AWS Activate Application — Sparc Energy
*Created: 2026-04-20 | Last modified: 2026-04-22*

**[DAN-89](https://linear.app/danbujoreanu/issue/DAN-89/dan-691-draft-aws-activate-application) | Deadline: 2026-04-25 | Submit at:** https://aws.amazon.com/activate/

---

## Application Tier

**AWS Activate Founders** (no AWS-affiliated VC/accelerator needed)
- Credits available: up to **$1,000 USD**
- Requirements: pre-revenue or early-stage startup, valid email, no prior Activate credits

> If you have or get a New Frontiers / Enterprise Ireland / SFI-backed accelerator offer before submitting, apply under **AWS Activate Portfolio** ($5,000–$25,000 tier) — the higher-value programme.

---

## Paste-Ready Application Fields

### Company / Product Name
```
Sparc Energy
```

### Website
```
https://energy.danbujoreanu.com
```
*(If not yet live, use your GitHub Pages or LinkedIn profile URL as a placeholder)*

### Stage
```
☑ Pre-product / MVP (prototype with real data, pre-revenue)
```

### Industry
```
Energy Technology / Clean Technology / IoT
```

---

### Product Description *(~500 characters — paste this)*

```
Sparc Energy is an AI-powered household energy management system for the Irish market. It forecasts electricity consumption 24 hours ahead (LightGBM, MAE 4.03 kWh, R²=0.975), identifies load-shifting opportunities, and actively controls smart devices (myenergi Eddi diverter) to minimise electricity costs. Validated on real smart meter data (Maynooth, Co Kildare). Target: €300–500/year savings per household. CRU's June 2026 dynamic pricing mandate is our product-market fit trigger.
```

---

### How will you use AWS credits? *(~500 characters — paste this)*

```
We will use AWS credits to deploy our production ML inference API on AWS App Runner (containerised FastAPI service), store time-series and user data on RDS PostgreSQL (eu-west-1, Ireland, GDPR-compliant), and implement our data ingestion pipeline on Lambda + S3. Our LightGBM model is trained locally; inference is lightweight (~50ms per request). Credits will fund 6–12 months of production infrastructure while we onboard our first 10 paying households and prepare for New Frontiers application.
```

---

### Technical Architecture *(for longer-form fields or follow-up — use as context)*

**Core ML pipeline (deployed):**
- LightGBM H+24 load forecasting — MAE 4.03 kWh, R²=0.975 (Drammen test set)
- Validated cross-city: Oslo MAE 7.41 kWh, R²=0.963
- DM significance test vs PatchTST: −12.17*** (HLN-corrected)

**API layer (ready to deploy):**
- FastAPI + uvicorn, Dockerised
- Endpoints: `/forecast`, `/control`, `/intel/query`, `/health`
- Docker image built, `apprunner.yaml` configured

**AWS services we plan to use:**
| Service | Use case |
|---------|----------|
| App Runner | Containerised API (no K8s overhead at early stage) |
| S3 | Smart meter CSV storage, model artefacts |
| RDS PostgreSQL (eu-west-1) | User data, household profiles, metering records |
| Lambda | Nightly forecast trigger, RSS feed ingestion |
| CloudWatch | Model drift monitoring (7d MAE > 1.5× threshold) |
| ECR | Docker image registry |
| Secrets Manager | API keys (myenergi, ESB Networks SMDS) |

**Data privacy:**
- All compute in eu-west-1 (Dublin) — GDPR Article 44 compliant (no cross-border transfers)
- 30-min smart meter data: never sent to external LLM APIs — only pre-computed stats

---

### Founder Background *(optional field — paste if asked)*

```
Dan Bujoreanu — MSc AI (NCI Dublin, 2026), MBA, BSc Computer Science. 10+ years product and engineering experience. PSPO I, PRINCE2. Building Sparc Energy as MSc thesis applied project and commercial MVP. Background: Meta (platform integrity), enterprise software. Research: journal paper submitted to Applied Energy / Energy and Buildings on ML load forecasting paradigm comparison.
```

---

### Use of Credits — Estimated Monthly AWS Cost

| Service | Instance/Config | Est. $/month |
|---------|----------------|-------------|
| App Runner | 0.25 vCPU / 0.5 GB, 1 instance | ~$5 |
| RDS db.t3.micro | PostgreSQL, eu-west-1 | ~$13 |
| S3 (5 GB) | Standard storage | ~$0.12 |
| Lambda | 1M req/month free tier | $0 |
| ECR | 1 GB storage | ~$0.10 |
| CloudWatch | Basic metrics | ~$1 |
| **Total** | | **~$20/month** |

$1,000 credit → ~**50 months** runway at MVP scale (well past first 10 paying customers).

---

## Submission Steps

1. Go to: https://aws.amazon.com/activate/founders/
2. Click **Apply now**
3. Enter email: `dan.bujoreanu@gmail.com`
4. Fill fields using the paste-ready text above
5. Under "AWS Account ID": use existing account or create one (free)
   - Your existing AWS account ID: check at https://console.aws.amazon.com → top-right menu → Account
6. Submit — approval typically 1–3 business days

---

## If You Get Rejected / Want Higher Tier

1. **New Frontiers Phase 1** (Enterprise Ireland accelerator, NCI): apply summer 2026 → becomes AWS Activate Portfolio eligible (~$5,000–$25,000)
2. **Dogpatch 2050 Accelerator** (ESB/Dogpatch Labs, equity-free): Jan 2027 cohort — Portfolio eligible
3. **SEAI RD&D call** (May–July 2026): research partner NCI — does not guarantee Activate Portfolio but adds credibility

---

*Created: 2026-04-20 | Last modified: 2026-04-22 | [DAN-89](https://linear.app/danbujoreanu/issue/DAN-89/dan-691-draft-aws-activate-application) | Owner: Dan Bujoreanu*
