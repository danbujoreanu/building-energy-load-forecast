# ADR-006: EU AI Act Limited Risk Classification (Art. 52)

**Status:** Accepted
**Date:** 2026-03-28

---

## Context

The EU AI Act (effective **August 2, 2026** — the date most obligations including Art. 50/52 transparency requirements come into force) classifies AI systems by risk level, with compliance obligations scaled accordingly. Q2 2026 guidelines from the AI Office are expected to clarify implementation details. Sparc Energy's LightGBM system needed to be classified before any product launch or Enterprise Ireland funding application, both to manage compliance obligations and to demonstrate regulatory fluency to enterprise clients and governance-focused employers.

The classification affects: conformity assessment requirements, documentation obligations, whether a third-party audit is required, and the technical measures needed before deployment.

---

## Options Considered

| Classification | Criteria | Obligations | Would apply if... |
|---------------|----------|------------|-------------------|
| **Prohibited** | Social scoring, biometric surveillance, etc. | Cannot deploy | Not applicable |
| **High Risk (Art. 6, Annex III)** | Critical infrastructure control, employment decisions, financial services access | Conformity assessment, human oversight, logging, third-party audit | System controlled safety-critical grid operations OR made autonomous credit/employment decisions |
| **Limited Risk (Art. 52)** | Systems that interact with users or generate/manipulate content, with transparency obligations | Transparency: disclose AI nature, show confidence, provide override | Recommends actions to users; does not control safety-critical infrastructure |
| **Minimal Risk** | Spam filters, games, etc. | No obligations | Not applicable given user-facing recommendations |

---

## Decision

**Limited Risk — Article 52.**

**Reasoning:**
- The system makes **recommendations** ("defer hot water heating to 14:00–16:00 when solar is forecast") — it does not directly control safety-critical infrastructure
- Automation level is **Level 2**: automated recommendations with optional automated execution, always user-configurable
- No decisions affecting employment, credit, education, or other Annex III high-risk domains
- No biometric data; energy consumption data is not listed as a special category under GDPR Art. 9

**Transparency obligations applied (Art. 52):**
1. Confidence ranges always displayed (P10/P50/P90)
2. Human override always available — user can disable automation at any time
3. Every automated action logged (MockDeviceConnector logs all commands; production will require persistent audit log)

**Note on future scope:** If Sparc Energy expands to grid-level balancing (directly controlling DSO/TSO systems), or to healthcare-adjacent applications (e.g., medical equipment load management), the classification should be re-evaluated for High Risk.

---

## Consequences

**Positive:**
- No conformity assessment required pre-launch — significantly reduces compliance burden for an early-stage startup
- No third-party technical audit required
- Documentation obligations (this doc, MODEL_CARD.md, DATA_PROVENANCE.md, DATA_LINEAGE.md) are sufficient for launch
- Classification documented in `docs/governance/AIIA.md` — ready for EI funding applications and Okta-style governance interviews

**Trade-offs:**
- Limited Risk classification relies on the system remaining advisory, not control-level. Architecture must not change to autonomous grid control without re-evaluation
- Art. 52 transparency requirements must be maintained in all production UIs — confidence ranges and override controls are non-optional
- As the EU AI Act evolves (implementing acts expected 2026–2027), this classification should be reviewed annually
