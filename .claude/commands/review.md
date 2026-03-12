# /review — Production Code Audit

Perform a structured production-readiness audit of the specified file or module.
If no file is specified, audit the most recently modified source file.

## Audit Checklist

### 1. Data Leakage (highest priority for ML pipelines)
- Are any lag/rolling features using data from the future relative to the forecast horizon?
- Does the scaler fit on train-only data, or does test data leak into fit()?
- Does OOF stacking use gap=168 to prevent lag_168h boundary leakage?
- Is the scaler loaded (not re-fit) during inference in connectors/live_inference.py?

### 2. Error Handling & Robustness
- Are all external API calls (OpenMeteo, SEMO, myenergi) wrapped in try/except with timeouts?
- Does the FastAPI app return meaningful error messages with correct HTTP status codes?
- Are missing feature columns handled gracefully (fill with 0 or raise with clear message)?
- Is the model file absence handled (clear FileNotFoundError, not AttributeError)?

### 3. Production Risk (from gstack /review pattern)
- Race conditions: can two /control requests corrupt shared state in ControlEngine?
- N+1 queries: does any loop call the database/file system per building instead of once?
- Trust boundaries: is any user-supplied input passed unsanitised to file paths or shell commands?
- Memory: are large DataFrames (model_ready.parquet) loaded once at startup or per request?

### 4. Config Hygiene
- Are all parameters read from config/config.yaml, nothing hardcoded?
- Are any API keys, file paths, or thresholds hardcoded as literals?
- Is n_features_lgbm: 35 enforced — does the code crash clearly if feature count mismatches?

### 5. Test Coverage Gaps
- Does this module have any unit tests in tests/?
- Are edge cases covered: empty DataFrame, single building, horizon=1, NaN-heavy inputs?

## Output Format
Produce a report with sections:
- CRITICAL (would cause wrong predictions or silent data corruption)
- WARNING (would cause crashes or poor UX in production)
- SUGGESTION (code quality, not urgent)
- CLEAN (explicitly confirm what is correct — don't only report problems)

End with a one-line verdict: READY / NEEDS WORK / BLOCKED.
