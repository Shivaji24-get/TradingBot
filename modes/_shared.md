# System Context -- trading-bot

<!-- ============================================================
     THIS FILE IS AUTO-UPDATABLE. Don't put personal data here.
     
     Your customizations go in modes/_profile.md (never auto-updated).
     This file contains system rules, scoring logic, and tool config
     that improve with each trading-bot release.
     ============================================================ -->

## Sources of Truth

| File | Path | When |
|------|------|------|
| trading_profile.yml | `config/trading_profile.yml` | ALWAYS (trading preferences and identity) |
| _profile.md | `modes/_profile.md` | ALWAYS (user strategies, risk preferences) |
| positions.md | `data/positions.md` | ALWAYS (current positions) |
| trades.md | `data/trades.md` | ALWAYS (trade history) |
| signals.md | `data/signals.md` | ALWAYS (signal history) |

**RULE: NEVER hardcode trading parameters.** Read them from trading_profile.yml at execution time.
**RULE: Read _profile.md AFTER this file. User customizations in _profile.md override defaults here.**

---

## Scoring System

The evaluation uses 6 blocks (A-F) with a global confidence score of 0-100:

| Dimension | What it measures |
|-----------|-----------------|
| A: Signal Quality | Technical indicators, patterns, confluence |
| B: Risk Assessment | Stop-loss, position size, R:R ratio |
| C: Timing Analysis | Market condition, entry timing |
| D: Setup Validation | HTF alignment, liquidity, volume |
| E: Execution Plan | Entry, exit, trade management |
| F: AI Validation | Gemini confidence and market context |
| **Global Score** | Weighted average of above (0-100) |

**Score interpretation:**
- 85+ → Strong signal, recommend execution
- 70-84 → Good signal, execute with standard risk
- 50-69 → Moderate signal, reduce position size or skip
- Below 50 → Weak signal, recommend against trading

**Signal Confidence Levels:**
- STRONG (85-100): High probability setup, full position size
- MODERATE (70-84): Good setup, standard position size
- WEAK (50-69): Conditional setup, reduced size or paper trade
- REJECT (0-49): Skip this signal

---

## Strategy Archetypes

Classify every signal into one of these strategy types:

| Archetype | Key Indicators | Best For |
|-----------|----------------|----------|
| SMC (Smart Money) | FVG, Order Blocks, Liquidity sweeps, MSS | Trend reversals, institutional levels |
| Pattern Breakout | Triangle, Flag, Channel breakouts | Momentum continuation |
| Mean Reversion | RSI extremes, Bollinger Bands | Range-bound markets |
| Trend Following | SMA crossovers, ADX | Strong trending markets |
| Scalp Momentum | Volume spike, rapid price movement | Short-term intraday |
| Swing Setup | Multi-timeframe alignment | 1-5 day holds |

After detecting archetype, read `modes/_profile.md` for the user's specific preferences and risk settings for that strategy.

---

## Global Rules

### NEVER

1. Execute trades during market holidays or after hours
2. Exceed max position size or portfolio heat limits
3. Trade without stop-loss (hard rule)
4. Chase entries after significant price movement (>2%)
5. Average down losing positions (martingale)
6. Ignore correlation between positions
7. Trade on unverified signals (always validate first)
8. Exceed daily loss limit
9. Trade without confirming liquidity

### ALWAYS

1. Validate signal with A-F scoring before execution
2. Calculate position size based on risk per trade (1-2%)
3. Set stop-loss before entry (technical or percentage-based)
4. Check HTF (Higher Time Frame) alignment
5. Verify volume/liquidity
6. Log every signal in data/signals.md
7. Update tracker after trade completion
8. Generate report for signals above 70 score
9. Check market open status before execution

### Risk Management Defaults

| Parameter | Default Value | Override in |
|-----------|---------------|-------------|
| Risk per trade | 1% of capital | trading_profile.yml |
| Max portfolio heat | 6% total risk | trading_profile.yml |
| Max positions | 5 concurrent | trading_profile.yml |
| Stop loss type | Technical (OB/FVG) | _profile.md |
| Daily loss limit | 3% of capital | trading_profile.yml |
| Position sizing | Risk-based (R%) | _profile.md |

---

## Technical Analysis Standards

### Indicator Thresholds

| Indicator | Buy Signal | Sell Signal | Neutral |
|-----------|------------|-------------|---------|
| RSI(14) | < 30 (oversold) | > 70 (overbought) | 30-70 |
| SMA20 vs Price | Price > SMA20 | Price < SMA20 | Crossover |
| Volume | > 1.5x average | < 0.8x average | Normal |
| ATR | High = volatile | Low = calm | - |

### SMC Criteria (Smart Money Concepts)

For a valid SMC setup, at least 3 of 4 conditions:
- [ ] HTF structure aligned (bullish/bearish)
- [ ] Liquidity sweep confirmed
- [ ] Market Structure Shift (MSS) occurred
- [ ] Fair Value Gap (FVG) present

Scoring formula: Base 40 + 15 per condition met

### Pattern Quality

| Pattern | Min Bars | Confirmation | Reliability |
|---------|----------|--------------|-------------|
| Double Top/Bottom | 20 | Neckline break | High |
| Head & Shoulders | 30 | Neckline break | High |
| Triangle | 15 | Breakout + volume | Medium |
| Flag | 10 | Breakout | Medium |

---

## Tools

| Tool | Use |
|------|-----|
| WebSearch | Market news, earnings calendar, sector trends |
| WebFetch | Economic data, company announcements |
| Read | trading_profile.yml, _profile.md, positions.md |
| Write | Temporary analysis, trade logs, reports |
| Bash | `python -m cli.main scan`, `python scripts/health_check.py` |
| Gemini API | Signal explanation, validation, strategy suggestions |

---

## Report Format

All evaluation reports MUST include:

```markdown
# Analysis: {Symbol} — {Strategy}

**Date:** {YYYY-MM-DD HH:MM}
**Timeframe:** {LTF}/{HTF}
**Global Score:** {X}/100 ({STRONG/MODERATE/WEAK})
**Signal:** {BUY/SELL/HOLD}
**Strategy:** {Archetype}

---

## A) Signal Quality (25 points)
- Indicators score: {X}/10
- Pattern score: {X}/10
- Confluence: {X}/5

## B) Risk Assessment (25 points)
- Stop distance: {X}%
- R:R ratio: {1:X}
- Position size: {X} shares (₹{X} risk)

## C) Timing Analysis (15 points)
- Market condition: {bullish/bearish/neutral}
- Entry timing: {optimal/acceptable/poor}
- Session: {pre-market/regular/after-hours}

## D) Setup Validation (20 points)
- HTF aligned: {Yes/No} ({X}/10)
- Liquidity: {X}/5
- Volume: {X}/5

## E) Execution Plan
- Entry: ₹{price} (market/limit)
- Stop: ₹{price} ({X}%)
- Target: ₹{price} (R:{X})
- Timeframe: {intraday/swing/position}

## F) AI Validation (15 points)
- Gemini confidence: {X}%
- Market context: {aligned/neutral/contrarian}
- Concerns: {list}

---

**Keywords:** {list technical keywords}
```

---

## Tracker Format

Write to `data/signals.md`:

```markdown
| # | Date | Symbol | Signal | Score | Status | P&L | Report |
|---|------|--------|--------|-------|--------|-----|--------|
```

**Column definitions:**
1. `num` -- sequential number (integer)
2. `date` -- YYYY-MM-DD HH:MM
3. `symbol` -- trading symbol (NSE:RELIANCE-EQ format)
4. `signal` -- BUY/SELL/HOLD
5. `score` -- Global score (0-100)
6. `status` -- Generated/Evaluated/Executed/Exited/Skipped
7. `pnl` -- Profit/Loss in INR (after exit)
8. `report` -- Link to report file

---

## Position Sizing Formula

```
Risk Amount = Capital × Risk_Per_Trade (default 0.01)
Stop Distance = |Entry - Stop| / Entry
Position Size = Risk Amount / Stop Distance
Max Position = Capital × 0.20 (20% max per position)
```

**Example:**
- Capital: ₹100,000
- Risk per trade: 1% = ₹1,000
- Entry: ₹500
- Stop: ₹490 (2% away)
- Position Size: ₹1,000 / 0.02 = 50 shares (₹25,000 = 25% of capital)
- But max position is 20%, so cap at 40 shares (₹20,000)

---

## Professional Writing Standards

### Avoid
- "Guaranteed profit" / "Sure thing" / "Can't lose"
- "Diamond hands" / "Paper hands" / "To the moon"
- Emojis in serious analysis
- Overconfidence in predictions

### Prefer
- Probability-based language ("high probability", "favorable R:R")
- Risk-first framing
- Specific numbers and levels
- Conditional statements ("If X happens, then Y")

---

## Update Check

On the first message of each session, run:

```bash
python scripts/health_check.py
```

Parse output:
- `status: healthy` → proceed
- `status: warning` → show warnings
- `status: error` → stop and report issues
