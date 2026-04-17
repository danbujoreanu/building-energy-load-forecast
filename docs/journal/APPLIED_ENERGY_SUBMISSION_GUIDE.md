# Applied Energy — Submission Guide for Sparc Energy Paper

**Target journal:** Applied Energy (Elsevier)
**Impact Factor:** 11.2 (2023) | Q1 Energy
**Paper working title:** Day-Ahead Load Forecasting for Norwegian Public Buildings with Demand-Response Control: An LightGBM Ensemble Approach
**Current state:** v0.9.0 — 8 sections drafted, journal paper in `docs/JOURNAL_PAPER_DRAFT.md`

---

## Journal Specifications

| Parameter | Value |
|-----------|-------|
| Word limit | 12,000 words (excluding abstract, references, captions) |
| Abstract | 250 words max |
| Keywords | 6 max |
| Figures | No formal limit — must be high resolution (300 dpi minimum) |
| References | No limit — use numbered Vancouver style |
| APC (Gold OA) | USD $3,150 (~€2,900) — waiver possible via Irish academic institutions |
| Submission system | Elsevier Editorial Manager (EES) |

---

## Desk Rejection Risk Factors (25–35% desk rejection rate)

Applied Energy desk-rejects papers that:
1. **Lack techno-economic analysis** — benchmark results alone are not sufficient. Must include €/kWh savings, payback periods, or demand-response value quantification. **Action: €178.65/yr home trial finding MUST be in the paper. Expand with cost-of-grid analysis.**
2. **No system integration context** — pure ML papers without deployment context are frequently rejected. **Mitigant: FastAPI deployment, MockDeviceConnector, myenergi Eddi live trial all in scope.**
3. **Narrow geographic scope without justification** — Norwegian buildings only may raise reviewer concern. **Mitigant: justify with ENTSO-E data availability and Norwegian grid's high renewable penetration = harder forecasting problem.**
4. **Prior publication overlap** — MSc thesis and AICS 2025 paper exist. Ensure submitted paper adds substantial novel contribution (journal paper = extended methodology + deployment + home trial results not in thesis/conference paper).

---

## Required Sections (Applied Energy structure)

1. **Abstract** (250 words) — problem, method, result, significance
2. **Introduction** — energy context, forecasting challenge, contribution statement
3. **Related Work** — ML for load forecasting; gap this paper fills
4. **Methodology** — feature engineering (oracle-safe lags ≥ 24h), LightGBM, OOF stacking, quantile regression
5. **Experimental Setup** — Drammen + Oslo buildings, train/test splits, DM test protocol
6. **Results** — R²=0.975 Drammen, R²=0.963 Oslo, DM test significance, P10/P50/P90 intervals
7. **Deployment + Home Trial** (CRITICAL — differentiator) — FastAPI, demand-response engine, myenergi Eddi integration, €178.65/yr saving
8. **Techno-Economic Analysis** (CRITICAL — desk rejection risk if absent) — savings model, scalability to building portfolio, EI/DSO value case
9. **EU AI Act Compliance Note** — Art. 52 Limited Risk classification, transparency obligations (P10/P90 display, human override) — differentiator vs competitor papers
10. **Conclusion + Future Work**

---

## Timeline

| Milestone | Target |
|-----------|--------|
| Draft complete (all 10 sections) | Apr–May 2026 |
| Internal review + figures | May–Jun 2026 |
| Submission | Jun–Jul 2026 |
| First decision (median 100–140 days) | Oct–Nov 2026 |
| Revision turnaround | ~30 days from decision |
| Publication | Q1 2027 (estimated) |

---

## APC Strategy

- **Option 1:** Check NCI + UCD Smurfit library agreements with Elsevier — Irish academic institutions often have APC waivers via national agreements (IReL consortium). Contact NCI library before submission.
- **Option 2:** Submit as subscription article (no APC) — access restricted but zero cost. Evaluate based on EI Innovation Voucher audience (EI may prefer OA).
- **Option 3:** Pay APC (~€2,900) — only if waivers fail and EI/Sparc pitch depends on visible publication.

---

## Figures to Generate

All figures in `scripts/generate_paper_figures.py`:

| Figure | Content | Status |
|--------|---------|--------|
| Fig 1 | Architecture diagram (data → features → model → control) | Needed |
| Fig 2 | Actual vs Predicted (Drammen, test period) | Script exists |
| Fig 3 | SHAP feature importance (LightGBM H+24) | Script exists |
| Fig 4 | P10/P50/P90 intervals (7-day window) | Needed |
| Fig 5 | Demand-response timeline (morning brief → Eddi action) | Needed |
| Fig 6 | Techno-economic: cumulative savings curve | Needed |

---

## Keywords (proposed)

`day-ahead load forecasting`, `LightGBM`, `demand response`, `EU AI Act`, `building energy management`, `quantile regression`

---

## Related File
- Full draft: `docs/JOURNAL_PAPER_DRAFT.md`
- Figures script: `scripts/generate_paper_figures.py`
- Outline: `docs/JOURNAL_PAPER_OUTLINE.md`
- Reviewer response matrix: `docs/REVIEWER_RESPONSE_MATRIX.md`
