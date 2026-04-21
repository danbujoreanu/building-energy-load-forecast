# Engineering Best Practices — Sparc Energy

> **Source authority:** Distilled from DocuSign (Apr 2026) and Intercom (Apr 2026) engineering posts,
> combined with lessons from this project's own code audit sessions.
> These are operational standards, not aspirational guidelines — every item has a "how to verify" check.

*Last updated: 2026-04-21*

---

## 1. CI/CD — The Foundation

### What we have
- `.github/workflows/ci.yml` — 3 jobs: **Tests**, **Code quality**, **Docker build**
- `.github/workflows/claude-review.yml` — AI code review on every PR (Pass 1: critical / Pass 2: informational)

### The Intercom principle
> *"We see velocity as a strong driver of stability. Downtime from breaking changes dropped 35% even as deployments doubled."*

Fast, frequent, small — that is the model. One large PR per week creates more risk than five small ones.

### Rules
1. **Every push to `main` triggers CI.** If CI is red, fix it before doing anything else.
2. **No merging with a failing CI run.** Set branch protection rules on GitHub → Require status checks to pass.
3. **Ship small.** A PR that changes one thing is easier to review, easier to revert, and faster to auto-approve (Intercom: auto-approved PRs close in 14.6 min vs 75.8 min median).
4. **Docker build runs in CI.** If the image doesn't build in CI, it won't deploy to App Runner.

### Coverage gate
Current threshold: **75%** (`--cov-fail-under=75`). This is a floor, not a target.
Raise it incrementally as test coverage improves. Do not lower it.

### GitHub Secrets required
| Secret | Used by | How to set |
|--------|---------|-----------|
| `ANTHROPIC_API_KEY` | `claude-review.yml` — AI PR reviewer | GitHub → Settings → Secrets → Actions |

---

## 2. Testing — The DocuSign Warning

### The anti-pattern that kills regression protection

DocuSign's team caught this on a 35-test suite that was **passing but providing zero protection**:
> *"Every single test is calling methods defined inside the test class itself. If the production parsing logic had a bug, none of those tests would catch it."*

**The fix:** Tests must import and call production module functions, not re-implement the logic.

### Verification command
```bash
# Find test files that define functions also tested within the same file
# (quick smell check — read the output critically)
grep -n "def test_" tests/*.py | head -40
grep -n "def _" tests/*.py | head -20  # helper functions inside test files are a warning sign
```

### Test taxonomy for this project

| Type | Location | What it tests | Runs in CI? |
|------|----------|--------------|-------------|
| Unit | `tests/test_*.py` | Single function, pure logic | ✅ Always |
| Integration | `tests/test_integration.py` | Full pipeline end-to-end, 12 scenarios | ✅ Always |
| API | `tests/test_api*.py` | FastAPI endpoints, request/response schemas | ✅ Always |
| Manual smoke | `make smoke-test` | Live Docker container `/health` → `/predict` | Before deploy |

### ML-specific testing rules
- **No data leakage in tests:** `make_splits()` must use `gap=168` for OOF stacking. Assert this.
- **Feature count is contract:** LightGBM expects exactly 35 features. Tests must verify `len(model.feature_name_) == 35`.
- **Scaler fit on train-only:** Never fit `StandardScaler` on val or test sets. Integration test covers this.
- **Drift detector independence:** `TestDriftDetectorIntegration` must pass on identical data (severity != CRITICAL) — this is a sanity check, not a real drift scenario.

### Coverage
```bash
# Run with coverage locally
pytest tests/ --cov=src/energy_forecast --cov-report=html
open htmlcov/index.html  # Browse which lines aren't covered
```

---

## 3. Code Quality

### Toolchain
| Tool | What it does | Config | Run |
|------|-------------|--------|-----|
| `ruff` | Linting (E/F/I/N/W/UP rules) | `pyproject.toml [tool.ruff]` | `ruff check src/ tests/ scripts/` |
| `black` | Formatting (line-length 100) | `pyproject.toml [tool.black]` | `black src/ tests/ scripts/` |
| `mypy` | Type checking (permissive — `ignore_missing_imports`) | `pyproject.toml [tool.mypy]` | `mypy src/energy_forecast/` |

### Pre-commit workflow (run before every push)
```bash
black src/ tests/ scripts/       # Format first
ruff check src/ tests/ scripts/ --fix   # Auto-fix safe lint issues
mypy src/energy_forecast/        # Type check (warnings, not errors yet)
pytest tests/ -q                 # Fast test run
```

### The DocuSign AI code review insight
> *"On medium-complexity PRs (6-10 changed files), our AI reviewer averaged 8.3 comments while human reviewers averaged 2.3 — a more than 3-to-1 gap. On the most complex PRs, where good feedback is most needed, an AI bot is often the dominant voice."*

We have `claude-review.yml` doing exactly this. It runs a **2-pass review**:
- **Pass 1 (Critical / blocks deployment):** Data leakage, feature count, city allowlist, model trust boundary
- **Pass 2 (Informational):** Concurrent safety, config coupling, dead code, test gaps

Read Claude's review before merging. Do not rubber-stamp resolve without reading.

### Magic numbers
All numeric constants (feature counts, horizon values, coverage thresholds, rate values) must live in:
- `config/config.yaml` — model hyperparameters and pipeline config
- `src/energy_forecast/tariff.py` — BGE rates (single source of truth)
- `deployment/mock_data.py` — shared mock curves

Never hardcode `35` (feature count), `168` (weekly lag), `24` (horizon), or tariff rates inline.

---

## 4. Deployment

### The Docker contract
```
Code change → ruff/black/mypy → pytest → docker build → docker run + /health → ECR push → App Runner
```

Every step must pass before the next. The `Makefile` has targets for each:
```bash
make docker-build      # Build image
make docker-smoke      # Run + hit /health
make ecr-push          # Push to ECR (needs AWS credentials)
make apprunner-deploy  # Deploy to App Runner
```

### The App Runner rule
Never push to ECR if `docker-smoke` fails. The App Runner will serve the broken image to real users.

### Model artefact discipline
- Active model in `outputs/models/` (local) or S3 (production — D-13).
- Registry manages CANDIDATE → ACTIVE → RETIRED lifecycle.
- No model goes ACTIVE without passing the 1.05× MAE regression gate.

### Blue/green via App Runner
App Runner does rolling replacement. To roll back: push the previous image tag to ECR, App Runner re-deploys within 60 seconds.

---

## 5. Observability

### The DocuSign pipeline principle
> *"Since we use a multi-step pipeline, errors at the beginning propagate and cause mistakes in later steps. We treat errors in the initial steps as higher priority than those later in the pipeline."*

For Sparc Energy, the pipeline steps in priority order:
1. **Data ingestion** (DAN-96 / CSVConnector) — if this fails, nothing else matters
2. **Feature engineering** (`build_temporal_features`) — silent NaN injection is a critical failure
3. **Inference** (LightGBM predict) — latency + NaN-in-prediction catch
4. **Control** (ControlEngine action) — must always have a safe fallback (`MAINTAIN_CURRENT`)

### What to monitor (Grafana — DAN-101 after DAN-96 has data)
| Metric | Alert threshold | Why |
|--------|---------------|-----|
| 7-day rolling MAE | > 1.5× training MAE | Drift trigger — retrain required |
| Night rate end missed | Any | Eddi boost fired at wrong rate |
| Solar irradiance vs actual | Δ > 30% | Weather connector degraded |
| API `/health` response time | > 2s | Container under memory pressure |
| Data gap | > 48h | Ingestion failure |

### Logging standard
Every `except` clause in a critical path must log with `logger.error(exc_info=True)`. No silent pass.
```python
# GOOD
except Exception as exc:
    logger.error("DriftDetector.full_report failed: %s", exc, exc_info=True)
    return DriftReport(severity=DriftSeverity.UNKNOWN)

# BAD
except Exception:
    pass
```

---

## 6. AI-Assisted Development

### We are Claude Code-first
All significant code changes go through Claude Code. This is the Intercom model:
> *"All technical work is becoming agent-first. This is the top priority for R&D."*

### What Claude Code is good at
- Implementing well-specified tasks (give it a docstring + test, get working code)
- Refactoring with constraints ("move this to a separate module, don't change the function signatures")
- Writing tests once you explain what the function must do
- Catching anti-patterns (DocuSign: 35 tests testing themselves)

### What requires your judgment
- Whether a feature should be built at all
- Architecture decisions (document in `docs/adr/`)
- Whether Claude's suggestion applies to *this* code or is a general pattern that doesn't fit

### The DocuSign PR navigator insight
When Claude's CI review flags something:
1. Read it alongside the **full function**, not just the flagged line
2. Ask: "Is this valid for *this specific code*, or is it a general pattern that doesn't apply here?"
3. If unsure: open a Claude conversation and discuss it — "rubber duck debugging where the duck talks back"
4. Never resolve a critical review comment without understanding the fix

---

## Source References

| Source | Article | Date | Key insight for Sparc |
|--------|---------|------|----------------------|
| DocuSign | "How I'm Using AI to Navigate AI Code Review" | Apr 21 2026 | CI-integrated AI reviewer; rubber duck debugging pattern; test anti-pattern |
| DocuSign | "How We Evaluate LLM Accuracy for Contract Review" | Apr 21 2026 | Precision/recall over accuracy; pipeline step priority; fast iteration with no-code testing |
| Intercom | "2× — nine months later: We did it" | Apr 16 2026 | Velocity = stability; auto-approved PRs; Claude Code-first engineering; cost per PR economics |

*File: `docs/engineering/BEST_PRACTICES.md` | Last updated: 2026-04-21*
