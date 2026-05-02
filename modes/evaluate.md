# Mode: evaluate — Signal Evaluation A-F

When the user provides a trade signal or symbol, deliver ALWAYS the 6 blocks (A-F evaluation):

## Paso 0 — Strategy Detection

Classify the signal into one of the strategy archetypes (see `_shared.md`). If hybrid, indicate the 2 closest. This determines:
- Which technical indicators to prioritize in Block A
- How to calculate stop-loss in Block B
- Which timeframe alignment matters most in Block D

## Block A — Signal Quality (25 points)

**Technical Indicators Score (10 points):**
- RSI position (0-3 points)
- SMA relationship (0-3 points)
- Volume confirmation (0-2 points)
- Additional indicators (0-2 points)

**Pattern Recognition (10 points):**
- Pattern clarity (0-4 points)
- Pattern completion (0-3 points)
- Historical reliability of this pattern (0-3 points)

**Confluence Factors (5 points):**
- Multiple indicators align (0-2 points)
- Multiple timeframe agreement (0-2 points)
- Sector/market alignment (0-1 point)

## Block B — Risk Assessment (25 points)

**Stop-Loss Quality (10 points):**
- Technical level (FVG, OB, swing high/low): 8-10 points
- Percentage-based (ATR multiple): 5-7 points
- Fixed amount: 0-4 points

**Risk:Reward Ratio (10 points):**
- R:R ≥ 3:1: 10 points
- R:R 2:1 to 3:1: 7-9 points
- R:R 1:1 to 2:1: 4-6 points
- R:R < 1:1: 0-3 points

**Position Sizing (5 points):**
- Risk-based sizing within limits: 5 points
- Risk slightly high but acceptable: 3-4 points
- Risk exceeds 2%: 0-2 points

## Block C — Timing Analysis (15 points)

**Market Condition (5 points):**
- Trend aligns with signal: 5 points
- Neutral/choppy: 2-3 points
- Trend against signal: 0-1 point

**Entry Timing (5 points):**
- Optimal entry zone: 5 points
- Acceptable entry: 3-4 points
- Chasing/poor timing: 0-2 points

**Session Quality (5 points):**
- High volume session: 5 points
- Normal session: 3-4 points
- Low volume/news risk: 0-2 points

## Block D — Setup Validation (20 points)

**Higher Timeframe Alignment (10 points):**
- HTF strongly aligned: 8-10 points
- HTF neutral: 4-7 points
- HTF against: 0-3 points

**Liquidity Assessment (5 points):**
- Above average volume: 4-5 points
- Normal liquidity: 2-3 points
- Low liquidity concern: 0-1 point

**Technical Structure (5 points):**
- Clean structure (no nearby resistance/support conflicts): 4-5 points
- Minor conflicts: 2-3 points
- Major conflict: 0-1 point

## Block E — Execution Plan (15 points)

Complete trade plan with:

| Element | Value | Quality Score |
|---------|-------|---------------|
| Entry Price | ₹{X} | (0-3 points) |
| Stop Loss | ₹{X} ({X}%) | (0-4 points) |
| Target 1 | ₹{X} (R:{X}) | (0-3 points) |
| Target 2 | ₹{X} (R:{X}) | (0-3 points) |
| Position Size | {X} shares | (0-2 points) |
| Timeframe | {intraday/swing} | (0-2 points) |
| Management | {trail/fixed/target} | (0-1 point) |

## Block F — AI Validation (15 points)

**Gemini Confidence Score (10 points):**
- If Gemini available: Generate AI assessment
- If unavailable: Use fallback logic based on pattern quality

**Market Context Alignment (5 points):**
- Check against broader market (Nifty trend, VIX, sector)
- Check correlation with existing positions

---

## Post-Evaluation

**ALWAYS** after generating blocks A-F:

### 1. Calculate Global Score
Sum A+B+C+D+E+F = Global Score (0-100)

### 2. Generate Report
Save to `reports/{###}-{symbol}-{YYYY-MM-DD}-eval.md`

Format:
```markdown
# Evaluation: {Symbol} — {Signal}

**Date:** {YYYY-MM-DD HH:MM}
**Score:** {X}/100 ({STRONG/MODERATE/WEAK/REJECT})
**Signal:** {BUY/SELL/HOLD}
**Strategy:** {Archetype}
**Recommendation:** {Execute/Watch/Paper/Skip}

---

## Score Breakdown

| Block | Points | Score |
|-------|--------|-------|
| A: Signal Quality | /25 | |
| B: Risk Assessment | /25 | |
| C: Timing Analysis | /15 | |
| D: Setup Validation | /20 | |
| E: Execution Plan | /15 | |
| F: AI Validation | /15 | |
| **TOTAL** | **/100** | **{X}** |

## A) Signal Quality
[full content]

## B) Risk Assessment
[full content]

## C) Timing Analysis
[full content]

## D) Setup Validation
[full content]

## E) Execution Plan
[full content]

## F) AI Validation
[full content]

## Final Recommendation

**Action:** {Execute with full size / Execute with reduced size / Paper trade / Skip}
**Reasoning:** [1-2 sentences]
**Key Risks:** [bullet list]
**Next Steps:** [what to watch for]
```

### 3. Register in Tracker
**ALWAYS** register in `data/signals.md`:
- Next sequential number
- Current date/time
- Symbol
- Signal type
- Global score
- Status: "Evaluated"
- P&L: —
- Report link

---

## Ethical Guidelines

- **NEVER guarantee profits** — Present probability, not certainty
- **ALWAYS quantify risk first** — Show potential loss before potential gain
- **Discourage overtrading** — If score < 50, explicitly recommend against trading
- **Quality over quantity** — One A-grade trade beats five C-grade trades
- **Respect user's risk limits** — Never suggest exceeding configured risk parameters
