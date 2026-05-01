# UX Voice & Tone Design Principles

**DAN-42 | Cross-cutting design standard — applies to every user-facing string in Sparc Energy.**

---

## The Standard in One Sentence

Every message Sparc Energy sends should feel like advice from a knowledgeable friend who happens to know your home — not a cost-reduction FAQ bot.

---

## The Target User

The design standard is written for a non-technical Irish household member — the person whose experience defines every copy decision.

- **Profile:** Mid-30s. Lives in a suburban Irish home with a partner. Has solar panels, doesn't know what kWh means.
- **Device fluency:** Reads messages on an iPhone. Uses WhatsApp and Pushover. Not a settings tweaker.
- **Energy mental model:** "My electricity costs too much. I vaguely know there are 'peak hours'. I'd act on a clear recommendation if I understood why."
- **Trust threshold:** Will act if (a) the reason is plain English, (b) they see a specific euro amount, and (c) there's an easy out ("No thanks").

This is **not** an engineer. This is **not** Dan.

---

## Voice Rules

### 1. Explain the *why* before the *what*

> ❌ "DEFER_HEATING at 17:00 (conf: 0.82)"
> ✅ "Your panels should cover hot water after 11am — waiting could save you €0.18 today."

The action only makes sense when the user understands the context. Lead with the reason.

### 2. Always state the euro amount

> ❌ "Shift EV charge to off-peak"
> ✅ "Charging overnight instead of now saves about €0.34 tonight."

One specific number is worth ten percentages. If the amount is uncertain, use a range: "~€0.20–0.40".

### 3. Never expose technical terms without plain-English context

Forbidden without a plain-English bracket: `kWh`, `P50`, `GHI`, `MPRN`, `SEMO`, `conf:`, `kW`.

> ✅ Allowed: "~3.5 kWh (enough to heat your tank from cold)"
> ❌ Forbidden: "3.5 kWh predicted diversion"

### 4. Every confidence signal is explained, not just shown

> ❌ "High confidence forecast"
> ✅ "We're fairly confident about this — your usage pattern has been consistent this week."

Use natural language hedges:
- High confidence → "We're fairly confident…"
- Medium → "It's likely that…"
- Low → "This is less certain — the weather forecast is mixed."

### 5. Every message has an out

Any message asking the user to act must have a visible decline path — "No thanks", "Dismiss", or "Remind me later". Invisible auto-actions are only permitted for zero-comfort-impact events (solar diversion).

### 6. Tone: warm, specific, low-drama

- Warm: "Heads up:" not "ALERT:"
- Specific: "between 5–7pm tonight" not "during peak hours"
- Low-drama: "could save you €0.18" not "MAXIMISE SAVINGS NOW"

---

## Application by Surface

### Morning Pushover Advisory

Current template (`morning_advisory.py`):

| Scenario | Compliant example |
|----------|-------------------|
| SKIP_BOOST | "☀️ Good sun tomorrow — your panels should fill the tank by noon. The 07:00 boost probably isn't needed. This could save ~17c (0.55 kWh × night rate)." |
| PARTIAL | "⛅ Mixed sun tomorrow — panels will warm the tank but may not fill it. Keep the 07:00 boost as a safety net. Solar should top it up during the day." |
| KEEP_BOOST | "☁️ Low sun expected tomorrow — panels won't do much. Keep the 07:00 boost running. No action needed." |

### Control Actions (`ControlAction.user_message`)

The `user_message` field (E-24) must follow the rules above. Example audit:

| Action | Non-compliant ❌ | Compliant ✅ |
|--------|-----------------|--------------|
| Defer Eddi boost | "DEFER_HEATING at 17:00" | "Your panels should cover hot water after 11am — waiting could save you €0.18 today." |
| EV shift | "Shift charge to 23:00 (night rate)" | "Charging after 11pm costs about 30c/kWh instead of 49c right now — saves ~€0.34 tonight." |
| Flex event | "Flex event 17:00–19:00. Reduce load." | "ESB is asking households to cut back 5–7pm tonight. Shifting your Eddi boost to 4pm instead saves ~€0.05 and helps the grid. [Accept] [No thanks]" |

### Tariff Comparison Output (`/compare-plans`)

- Lead with savings: "If you switch to SSE, you'd save about €74/year based on your last 2 years of usage."
- Explain the cap impact in plain language: "Your Saturday usage hit the BGE 100 kWh free limit in 3 months last year — that extra usage was billed at the day rate."
- Never show raw `annualised_cost_eur` without a label: "Annual cost on this plan: ~€1,240"

### Forecast (`/forecast/{household_id}`)

- P50 → "Most likely" or "Expected"
- P10 / P90 → "Best case" / "Worst case" or just show the range: "Expected: 12–18 kWh"

---

## Pre-Ship Copy Review Checklist

Before any new user-facing string ships, verify:

- [ ] No raw technical terms without plain-English context
- [ ] Euro amount present (or explicit "no financial impact")
- [ ] Reason stated before action
- [ ] Decline / dismiss path visible (for actionable messages)
- [ ] Read aloud by a non-technical person — does it make sense?
- [ ] Tone: warm, specific, low-drama ✓

---

## Ownership

| Function | Responsibility |
|----------|---------------|
| Design | Voice & tone review on all new message templates |
| Product | Gate new features on copy review before ship |
| Engineering | `ControlAction.user_message` populated (E-24 done ✅); no raw technical strings |
| Marketing | Brand voice consistency across in-app + Pushover + email |

---

## Success Metrics (tracked via DAN-43 Prediction Outcome Tracking)

- Recommendation acceptance rate ≥ 40% of shown recommendations
- User NPS ≥ 45 in first cohort survey
- Zero support tickets citing "I didn't understand what to do"

---

*Last updated: 2026-05-01 | DAN-42 | Status: Design standard locked*
