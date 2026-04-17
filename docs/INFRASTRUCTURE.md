# Infrastructure Decision Record

**Decision date:** 2026-04-18  
**Status:** DECIDED  
**Owner:** Dan Bujoreanu

---

## Decision: Hybrid Mac Mini + AWS (not AWS-only)

### Recommended stack

| Layer | Platform | Rationale |
|-------|----------|-----------|
| **Compute (FastAPI + Gradio + ML inference)** | Mac Mini M4 Pro 24GB | One-time €1,299; €5/month electricity; payback 18 months vs App Runner |
| **S3 — model artefacts** | AWS eu-west-1 | < €1/month at this scale; correct tool for versioned binaries |
| **Secrets Manager** | AWS eu-west-1 | €0.40/secret/month; audit trail; rotation support |
| **CloudWatch — drift alerts** | AWS eu-west-1 | €1–2/month; SNS email on MAE breach |
| **ECR — container registry** | AWS eu-west-1 | Free tier covers all images |
| **Database (Postgres + Redis)** | Mac Mini (Docker) | Until 500+ users, then evaluate RDS |
| **Vector store (ChromaDB)** | Mac Mini (Docker) | Local; backed up to S3 nightly |
| **Networking** | Cloudflare Tunnel | Free; replaces static IP requirement; handles TLS |

### Cost comparison

| Scenario | Monthly cost | Notes |
|----------|-------------|-------|
| Mac Mini M4 Pro 24GB (one-time €1,299) | ~€5 electricity + €5 AWS managed services | **Recommended** |
| AWS App Runner (always-on) | €30–60 | Scales well but expensive pre-revenue |
| Mac Mini + AWS Activate ($5k credits) | €0 for 12+ months | Apply DAN-69 immediately |

**Do NOT use App Runner until MRR > €500/month.** At that point, the operational overhead of self-hosting outweighs the cost saving.

---

## Mac Mini: M4 vs M5, 16GB vs 24GB

### M4 vs M5

| Factor | M4 (available now) | M5 (timing uncertain) |
|--------|-------------------|----------------------|
| Availability | Immediate (Apple Store) | Not officially announced as of April 2026 |
| Performance for this use case | Excellent | Likely ~20-30% faster |
| Recommendation | **Buy M4 now** | Don't wait — M5 release date unknown |

**Verdict: Buy Mac Mini M4 Pro now.** The performance difference won't matter for LightGBM inference (already < 50ms). Waiting 6-12 months for M5 means 6-12 months of not having your own always-on server.

### 16GB vs 24GB RAM

| Use case | 16GB | 24GB |
|---------|------|------|
| FastAPI + Gradio + Redis + Postgres + ChromaDB | ✅ Uses ~4GB peak | ✅ |
| LightGBM inference | ✅ < 200MB | ✅ |
| TFT/PyTorch DL training | ⚠️ Tight with 5yr dataset | ✅ Comfortable |
| Local open-source LLM (7B, 4-bit quantized) | ✅ ~5GB VRAM | ✅ |
| Local open-source LLM (14B, 4-bit) | ⚠️ ~10GB VRAM, tight | ✅ |
| Local open-source LLM (27-32B, 4-bit) | ❌ ~16-18GB VRAM, OOM | ✅ Minimum for 27B |
| Local open-source LLM (70B, 4-bit) | ❌ ~40GB required | ❌ Need M4 Ultra |

**Verdict: Get Mac Mini M4 Pro 24GB (€1,299).**  
Reasoning:
- €550 extra over M4 16GB gives you: comfortable DL training + local 27B model inference
- Local 27B models (Mistral-Small, Qwen2.5-32B) are viable for energy advisor at zero API cost
- If sticking to Gemini/Claude API only: 16GB is sufficient, but 24GB future-proofs for 3 years
- 256GB SSD is correct minimum — store model weights on external SSD (Crucial X9 Pro 1TB ~€80)

### Recommended hardware list

| Item | Cost | Source |
|------|------|--------|
| Mac Mini M4 Pro 24GB | ~€1,299 | Apple Store |
| Crucial X9 Pro 1TB external SSD | ~€80 | Amazon/Argos |
| APC UPS Back-UPS 650VA | ~€80 | Amazon |
| USB-C hub (for P1 adapter + peripherals) | ~€30 | Amazon |
| DSMR P1 USB adapter | ~€12 | tinytronics.nl |
| **Total** | **~€1,501** | |

---

## AWS Activate — Apply Immediately

- URL: aws.amazon.com/activate (Founders tier, no company required)
- Credits: $1,000–$5,000 USD
- Covers: S3, Secrets Manager, CloudWatch, ECR for 12+ months
- Apply before April 25, 2026 (before beta user costs begin)
- See DAN-69

---

## Network Architecture (Mac Mini production)

```
Internet
  ↓
Cloudflare CDN (DDoS protection, TLS termination, caching)
  ↓
cloudflared tunnel (running on Mac Mini)
  ↓ 
Nginx reverse proxy (Mac Mini localhost)
  ├── :8000 → sparc-api (FastAPI)
  ├── :7860 → sparc-demo (Gradio public demo) → energy.danbujoreanu.com
  └── :7861 → sparc-intel (Gradio private) → intel.danbujoreanu.com [Cloudflare Access]

Mac Mini Docker stack:
  sparc-api ↔ postgres:5432
  sparc-api ↔ redis:6379
  sparc-api ↔ chromadb (volume mount)
  sparc-api ↔ s3 (model artefacts, async)
  sparc-api ↔ AWS Secrets Manager (startup only)
  sparc-api ↔ CloudWatch (metrics push, async)
```

---

## mySigen / Sigenergy Integration

**Not a competitor — integration target.**

Sigenergy has a public REST API (developer.sigencloud.com) supporting VPP-style dispatch. For Sigenergy battery owners:
- Read: battery SoC, solar generation, grid consumption every 5 minutes
- Write: charge/discharge schedule (up to 2,000 simultaneous commands)
- Integration path: add `SigenConnector` in `deployment/connectors.py` alongside `EddiConnector`

**Solar + battery customer segment note:**  
A household with 10 solar panels + 10kWh battery is largely self-sufficient in summer. Sparc's optimization value is **lower** for this segment (battery absorbs tariff variation). Prioritise:  
1. **Tier 1:** Heat pump + EV owners (largest bills, most deferrable load)  
2. **Tier 2:** Solar without battery (export timing + consumption shift)  
3. **Tier 3:** Solar + large battery (value mainly in winter/cloudy periods)  

---

## Ento.ai — Commercial Segment Watch

Ento.ai is the best-practice benchmark for commercial building AI in Europe (55k+ buildings, $3.6M seed). They do anomaly detection and M&V — **not load forecasting, not device control**.

**Action for Sparc:**
- No action required for Phase 1 (residential/SME focus)  
- If entering Irish commercial portfolios (Phase 3): benchmark against Ento's IPMVP M&V capability  
- Watch for Irish market entry signals  

See `docs/COMPETITORS.md` for full analysis.
