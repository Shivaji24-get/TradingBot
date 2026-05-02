# Mode: risk — Risk Assessment and Management

Comprehensive risk assessment for open positions and potential trades.

## Risk Assessment Types

### Type 1: Portfolio Risk Overview

**Overall Portfolio Heat:**
```
Current Portfolio Risk Summary
══════════════════════════════════════════════════════════
Total Capital:        ₹{X}
Invested Capital:     ₹{X} ({X}%)
Available Cash:       ₹{X}

Risk Metrics:
├── Total Portfolio Heat:     {X}% / {max}% limit
├── Daily P&L:                ₹{X} ({X}%)
├── Open Position Risk:       ₹{X}
├── Distance to Stop (avg):   {X}%
└── Correlation Risk:         {Low/Medium/High}
```

**Position Concentration:**
```
Position Size Distribution:
Symbol 1: ₹{X} ({X}%) ████████████████████
Symbol 2: ₹{X} ({X}%) ██████████████
Symbol 3: ₹{X} ({X}%) ████████
...
```

### Type 2: Single Position Risk

**For a specific position:**

```
Risk Assessment: {Symbol} {Side}
══════════════════════════════════════════════════════════

Position Details:
├── Entry Price:      ₹{X}
├── Current Price:    ₹{X}
├── Stop Loss:        ₹{X}
├── Target:           ₹{X}
├── Quantity:         {X}
├── Position Value:   ₹{X}
└── Unrealized P&L:   ₹{X} ({X}%)

Risk Metrics:
├── Distance to Stop:     {X}% ({X} ₹)
├── Distance to Target: {X}% ({X} ₹)
├── R:R Ratio:          1:{X}
├── Position Heat:      {X}% of portfolio
├── Time in Trade:      {X} hours/days
└── Time to Target:     {estimate}

Scenario Analysis:
├── Stop Hit:           -₹{X} ({-X}% portfolio)
├── Target Hit:       +₹{X} ({+X}% portfolio)
├── Breakeven:          ₹{X}
└── 50% of Target:    +₹{X}
```

### Type 3: Pre-Trade Risk Assessment

**Before entering a new trade:**

**Risk Checklist:**
- [ ] Risk per trade ≤ 2% of capital
- [ ] Position size ≤ 20% of portfolio
- [ ] Total portfolio heat ≤ 6%
- [ ] R:R ratio ≥ 2:1
- [ ] Correlation with existing positions acceptable
- [ ] Market volatility normal (VIX < 25)
- [ ] Sufficient liquidity
- [ ] Stop-loss level clearly defined

**Impact Simulation:**
```
If this trade is executed:

Current Portfolio Heat:  {X}%
After This Trade:        {X}%  ← Must be ≤ 6%

Current Daily P&L:       ₹{X}
Max Loss (stop hit):    -₹{X}
New Daily P&L:          ₹{X} to -₹{X}

Correlation Check:
├── Existing positions in same sector: {list}
├── Correlation coefficient: {X}
└── Diversification impact: {positive/negative}
```

## Risk Calculation Formulas

### Portfolio Heat
```
Portfolio Heat = Σ (Position Risk)
Position Risk = |Entry - Stop| × Quantity
```

### Risk of Ruin (simplified)
```
RoR ≈ (1 - Win Rate)^(Max Consecutive Losses)
Or use formula: RoR = ((1 - Edge)/(1 + Edge)) ^ CapitalUnits
```

### Kelly Criterion (position sizing)
```
Kelly % = (Win Rate × Avg Win - Loss Rate × Avg Loss) / Avg Win
Fractional Kelly (1/4 to 1/2) recommended for safety
```

### Value at Risk (VaR)
```
Parametric VaR = Portfolio Value × Z-score × σ
Historical VaR = Xth percentile of historical returns
```

## Risk Alerts

**Generate alerts for:**
- Portfolio heat approaching limit (> 80% of max)
- Position size > 20% of portfolio
- Any position down > 3R
- Daily loss approaching limit (> 80%)
- Correlation risk (multiple correlated positions)
- Overnight risk (positions held overnight)

## Risk Report Format

```markdown
# Risk Assessment Report

**Date:** {YYYY-MM-DD HH:MM}
**Assessment Type:** {Portfolio/Position/Pre-Trade}

---

## Executive Summary
Risk Level: {Low/Moderate/High/Critical}
Key Concerns: {bullet list}
Recommendations: {bullet list}

## Portfolio Metrics

| Metric | Current | Limit | Status |
|--------|---------|-------|--------|
| Portfolio Heat | {X}% | 6% | ✓/⚠/✗ |
| Daily P&L | {X}% | 3% | ✓/⚠/✗ |
| Max Position | {X}% | 20% | ✓/⚠/✗ |
| Consecutive Losses | {X} | 3 | ✓/⚠/✗ |

## Position Risk Details

| Symbol | Side | Size | Heat | R:R | Status |
|--------|------|------|------|-----|--------|
| ... | ... | ... | ... | ... | ... |

## Scenario Analysis

### Best Case (10% probability)
All positions hit target: +₹{X}

### Base Case (50% probability)
Mixed outcomes: +₹{X} to -₹{X}

### Worst Case (10% probability)
All stops hit: -₹{X}

## Recommendations
1. [Action item 1]
2. [Action item 2]
3. [Action item 3]

---
**Next Review:** {time}
```

## Risk Management Rules

### Hard Rules (Never Violate)
1. **Stop Loss:** Every position MUST have a stop-loss
2. **Position Limit:** No single position > 20% of portfolio
3. **Heat Limit:** Total portfolio heat never exceeds 6%
4. **Daily Loss:** Stop trading after 3% daily loss
5. **Correlation:** No more than 2 correlated positions

### Soft Rules (Guidelines)
1. Prefer R:R ≥ 3:1
2. Avoid first 15 minutes volatility
3. Reduce size in high volatility (VIX > 20)
4. Trail stops after 2R profit
5. Take partial profits at 3R

### Emergency Procedures
1. **Market Crash:** Close all positions immediately
2. **System Failure:** Manual exit via broker app
3. **Losing Streak:** Reduce size by 50% after 3 losses
4. **Overtrading:** Mandatory 1-hour break after 5 trades

## CLI Commands

```bash
# Portfolio risk overview
python -m cli.main risk

# Single position risk
python -m cli.main risk --symbol NSE:RELIANCE-EQ

# Pre-trade assessment
python -m cli.main risk --trade "BUY NSE:SBIN-EQ at 650, stop 640"

# Set risk alert
python -m cli.main risk --alert --heat 80
```
