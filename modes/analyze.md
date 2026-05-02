# Mode: analyze — Deep Market Analysis

Execute comprehensive AI-powered analysis of a symbol or market condition.

## Analysis Types

### Type 1: Symbol Deep Dive

**For a specific symbol (e.g., "NSE:RELIANCE-EQ"):**

**Multi-Timeframe Analysis:**
- Daily: Long-term trend, key levels
- 4H: Swing structure
- 1H: Entry/exit zones
- 15M/5M: Precise timing

**Technical Components:**
1. Trend Analysis
   - Current trend direction and strength (ADX)
   - Trend phase (early, mature, late)
   - Key swing highs/lows

2. Support/Resistance Levels
   - Major horizontal levels
   - Trendlines
   - Moving averages as dynamic S/R
   - Fibonacci levels (if relevant)

3. Volume Analysis
   - Volume trend
   - Significant volume spikes
   - Volume at key levels

4. Pattern Analysis
   - Active patterns
   - Historical pattern reliability
   - Pattern completion probability

5. Indicator Dashboard
   - RSI: position and divergence
   - MACD: signal line cross, histogram
   - SMA: alignment (golden/death cross)
   - Bollinger Bands: squeeze/breakout

6. SMC Analysis (if enabled)
   - Higher timeframe structure
   - Liquidity zones
   - Fair Value Gaps
   - Order Blocks
   - Recent Market Structure Shifts

**Market Context:**
- Nifty 50 trend correlation
- Sector performance
- Recent news/earnings impact
- Institutional activity (if detectable)

### Type 2: Market Condition Analysis

**For broader market (e.g., "Nifty trend"):**

**Components:**
1. Index Analysis (Nifty 50, Bank Nifty)
   - Trend direction and strength
   - Key levels (support/resistance)
   - Market breadth

2. Volatility Assessment
   - VIX or realized volatility
   - ATR trends
   - Expected range

3. Sector Rotation
   - Leading sectors
   - Lagging sectors
   - Flow indicators

4. Market Structure
   - Higher highs/higher lows (bullish)
   - Lower highs/lower lows (bearish)
   - Consolidation patterns

5. Key Events Calendar
   - Upcoming earnings
   - Economic data releases
   - RBI/policy events

### Type 3: Comparative Analysis

**Compare 2-3 symbols:**
- Relative strength
- Correlation
- Which offers better R:R
- Sector comparison

## AI Enhancement

**Gemini Integration:**
```python
from core.gemini_advisor import GeminiAdvisor

# Get AI insights
advisor = GeminiAdvisor()
insights = advisor.deep_analysis(symbol, market_data)
```

**AI Outputs:**
- Narrative summary of technical picture
- Scenario analysis (bullish/bearish/base case)
- Key levels to watch
- Risk factors
- Time-based probabilities

## Report Structure

```markdown
# Deep Analysis: {Symbol}

**Date:** {YYYY-MM-DD HH:MM}
**Timeframes:** {D/4H/1H/15M/5M}
**Analysis Type:** {Symbol/Market/Comparative}

---

## Executive Summary
2-3 paragraph overview with key conclusions

## Multi-Timeframe Analysis

### Daily (Trend)
- Trend: {description}
- Key levels: {support} / {resistance}
- Structure: {bullish/bearish/neutral}

### 4H (Swing)
- Recent structure
- Active patterns
- Momentum

### 1H (Setup)
- Entry zones
- Stop placement
- Target levels

### 15M/5M (Timing)
- Microstructure
- Immediate levels
- Entry timing

## Technical Dashboard

| Indicator | Value | Signal | Strength |
|-----------|-------|--------|----------|
| RSI(14) | XX | overbought/oversold/neutral | strong/moderate/weak |
| SMA(20) | ₹X | above/below price | — |
| SMA(50) | ₹X | golden/death cross | — |
| MACD | X | bullish/bearish/neutral | strong/moderate/weak |
| ATR(14) | ₹X | high/low volatility | — |

## SMC Analysis (if enabled)

| Component | Status | Level | Quality |
|-----------|--------|-------|---------|
| HTF Trend | Bullish/Bearish | — | Strong/Weak |
| Liquidity | Swept/Unswept | ₹X | — |
| MSS | Confirmed/Pending | ₹X | — |
| FVG | Present/Absent | ₹X-X | High/Low |
| OB | Present/Absent | ₹X | High/Low |

## Key Levels

### Support
1. Major: ₹X (source: weekly low)
2. Minor: ₹X (source: daily SMA)

### Resistance
1. Major: ₹X (source: all-time high)
2. Minor: ₹X (source: recent swing high)

### Pivot Points
- Daily PP: ₹X
- R1: ₹X | R2: ₹X
- S1: ₹X | S2: ₹X

## Scenario Analysis

### Bullish Case (30% probability)
- Trigger: {what needs to happen}
- Target: ₹X
- Invalidation: ₹X

### Base Case (50% probability)
- Expectation: {most likely outcome}
- Range: ₹X - ₹X

### Bearish Case (20% probability)
- Trigger: {what needs to happen}
- Target: ₹X
- Invalidation: ₹X

## Trading Opportunities

| Setup | Direction | Entry | Stop | Target | R:R | Quality |
|-------|-----------|-------|------|--------|-----|---------|
| Setup 1 | Long/Short | ₹X | ₹X | ₹X | X:1 | A/B/C |

## Risk Factors
- [ ] Factor 1
- [ ] Factor 2

## AI Insights (Gemini)
[Natural language analysis and suggestions]

## Action Items
- [ ] Watch for X level break
- [ ] Monitor volume at Y
- [ ] Set alert for Z

---
**Next Update:** {suggested time}
**Confidence:** {High/Medium/Low}
```

## Output

Save to: `reports/{###}-{symbol}-{YYYY-MM-DD}-analysis.md`

Update tracker with analysis reference.
