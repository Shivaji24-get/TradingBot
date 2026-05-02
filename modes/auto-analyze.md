# Mode: auto-analyze — Automatic Signal Analysis Pipeline

When the user pastes a trade signal or symbol, execute the FULL PIPELINE automatically.

## Pipeline Stages

### Stage 1: Parse Input

**Detect input type:**

| Input Pattern | Type | Example |
|--------------|------|---------|
| "NSE:XXX-EQ" | Symbol only | "NSE:RELIANCE-EQ" |
| "BUY/SELL + symbol" | Preliminary signal | "BUY NSE:SBIN-EQ at 650" |
| "symbol + indicators" | Rich signal data | "NSE:TCS-EQ RSI 28, SMA cross" |
| Full JSON | Structured data | `{symbol, signal, indicators}` |

**Extract:**
- Symbol
- Suggested signal (if any)
- Price levels (if any)
- Indicators (if any)

### Stage 2: Fetch Market Data

For the detected symbol:
1. Get current quote (price, change, volume)
2. Load historical candles (primary timeframe)
3. Load HTF candles for bias
4. Get market snapshot (Nifty trend, sector)

### Stage 3: Technical Analysis

**Calculate indicators:**
- RSI(14)
- SMA(20) and SMA(50)
- Volume ratio vs average
- ATR(14)

**Detect patterns:**
- Check for active patterns
- Calculate pattern confidence

**Apply enabled strategies:**
- SMC: Check FVG, OB, MSS, liquidity
- Patterns: Breakout setups
- Mean reversion: RSI extremes

### Stage 4: A-F Evaluation

Run complete evaluation per `modes/evaluate.md`:
- Block A: Signal Quality (25 pts)
- Block B: Risk Assessment (25 pts)
- Block C: Timing Analysis (15 pts)
- Block D: Setup Validation (20 pts)
- Block E: Execution Plan (15 pts)
- Block F: AI Validation (15 pts)

**Generate:**
- Global score (0-100)
- Recommendation (Execute/Reduce/Paper/Skip)
- Complete trade plan

### Stage 5: Gemini AI Analysis (if available)

**If GEMINI_API_KEY configured:**
```python
from core.gemini_advisor import GeminiAdvisor
advisor = GeminiAdvisor()
explanation = advisor.explain_signal(symbol, signal_data)
validation = advisor.validate_signal(signal_data, market_context)
sizing = advisor.suggest_position_size(signal_data, portfolio)
```

**AI outputs:**
- Natural language signal explanation
- Multi-factor validation
- Position sizing suggestion

### Stage 6: Report Generation

**Save to:** `reports/{###}-{symbol}-{YYYY-MM-DD}-auto.md`

**Report includes:**
1. Header with score and recommendation
2. A-F evaluation blocks
3. AI analysis (if available)
4. Trade plan with exact levels
5. Risk warnings
6. Alternative scenarios

### Stage 7: Tracker Registration

**ALWAYS register:**
```markdown
| # | Date | Symbol | Signal | Score | Status | P&L | Report |
|---|------|--------|--------|-------|--------|-----|--------|
| 001 | 2026-01-15 10:30 | NSE:RELIANCE-EQ | BUY | 82 | Evaluated | — | [001](reports/001-reliance-2026-01-15-auto.md) |
```

**Status flow:**
- Generated → Auto-pipeline started
- Evaluated → A-F complete
- Executed → Order placed
- Exited → Position closed

### Stage 8: Notification (if configured)

**If notifications enabled:**
- Telegram alert for strong signals (≥75)
- Include summary + report link
- Option for one-tap execution link

## Auto-Execute Rules

**Only auto-execute if ALL conditions met:**
1. Global score ≥ 80 (STRONG)
2. No risk limit violations
3. Auto-trade enabled in config
4. Paper or live mode configured
5. Market is open
6. Not duplicate signal (within 1 hour)

**Auto-execute steps:**
1. Place paper trade (if paper mode)
2. Or place live order (if live mode confirmed)
3. Log to positions.md
4. Set stop-loss order
5. Send confirmation notification

## User Output

**Immediate response:**
```
🔍 Auto-Analysis Complete: NSE:RELIANCE-EQ

📊 Score: 82/100 (STRONG)
📈 Signal: BUY
🎯 Entry: ₹2,450 | Stop: ₹2,420 (1.2%) | Target: ₹2,550 (4x)

✅ Recommendation: EXECUTE with standard size

📄 Full report: reports/001-reliance-2026-01-15-auto.md
📋 Registered in tracker as #001

⚡ One-tap execution: [Execute Paper] [Execute Live]
```

## Pipeline Integrity

**Rules:**
1. Never skip evaluation on auto-pipeline
2. Always save report
3. Always register in tracker
4. Never auto-execute without user confirmation (unless explicitly enabled)
5. Log all pipeline stages for debugging

## Ethical Guidelines

- Present score and probability, not certainty
- Always show risk before reward
- For scores 50-69, suggest paper trading
- For scores < 50, explicitly recommend skipping
- Never override user's daily loss limits
