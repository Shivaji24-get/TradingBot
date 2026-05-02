# Mode: compare — Trade Setup Comparison

Compare and rank multiple trade setups side by side.

## Use Cases

1. **Multiple Signals:** When scanner finds several opportunities
2. **Symbol Selection:** Choosing which stock to trade
3. **Strategy Comparison:** Same symbol, different strategies
4. **Timeframe Analysis:** Same symbol, different timeframes

## Comparison Process

### Input Parsing

**Accept multiple formats:**
```
# Format 1: Space-separated symbols
/trading-bot-compare "RELIANCE TCS SBIN HDFCBANK"

# Format 2: Rich signal data
/trading-bot-compare "RELIANCE BUY @ 2450, TCS SELL @ 3850, SBIN BUY @ 650"

# Format 3: JSON-like
/trading-bot-compare "{symbol: RELIANCE, signal: BUY}, {symbol: TCS, signal: SELL}"
```

### Evaluation Pipeline

**For each setup:**

1. **Run Full A-F Evaluation**
   - Signal Quality (25 pts)
   - Risk Assessment (25 pts)
   - Timing Analysis (15 pts)
   - Setup Validation (20 pts)
   - Execution Plan (15 pts)
   - AI Validation (15 pts)

2. **Calculate Composite Score**
   - Base: A-F total (0-100)
   - Bonus: HTF alignment (+0-5)
   - Bonus: Volume confirmation (+0-5)
   - Penalty: Distance from optimal entry (-0-10)

3. **Risk-Adjusted Ranking**
   - Apply Kelly-like adjustment
   - Factor in R:R ratio
   - Consider portfolio fit

### Comparison Table

**Standard Comparison:**
```markdown
# Trade Setup Comparison

| Rank | Symbol | Signal | Score | R:R | Risk | HTF | Volume | Conv. | Rec. |
|------|--------|--------|-------|-----|------|-----|--------|-------|------|
| 🥇 1 | RELIANCE | BUY | 87 | 3.2 | 1.2% | ✅ | 1.8x | High | A |
| 🥈 2 | TCS | SELL | 82 | 2.8 | 1.5% | ✅ | 2.1x | Med | A |
| 🥉 3 | SBIN | BUY | 76 | 2.5 | 1.8% | ⚠️ | 1.2x | Med | B |
| 4 | HDFCBANK | SELL | 68 | 1.9 | 2.1% | ❌ | 0.9x | Low | C |
```

**Detailed Comparison:**
```markdown
## Detailed Scoring

| Metric | RELIANCE | TCS | SBIN | HDFCBANK |
|--------|----------|-----|------|----------|
| **Signal Quality** | | | | |
| Indicators | 9/10 | 8/10 | 7/10 | 6/10 |
| Pattern | 9/10 | 8/10 | 7/10 | 5/10 |
| Confluence | 5/5 | 4/5 | 4/5 | 3/5 |
| **Risk Assessment** | | | | |
| Stop Quality | 9/10 | 8/10 | 7/10 | 6/10 |
| R:R Ratio | 10/10 | 8/10 | 7/10 | 5/10 |
| Position Size | 5/5 | 5/5 | 4/5 | 3/5 |
| **Setup Validation** | | | | |
| HTF Aligned | 10/10 | 9/10 | 7/10 | 4/10 |
| Liquidity | 5/5 | 5/5 | 4/5 | 3/5 |
| Structure | 5/5 | 5/5 | 4/5 | 4/5 |

**TOTAL SCORES:**
| RELIANCE | TCS | SBIN | HDFCBANK |
|----------|-----|------|----------|
| 87/100 | 82/100 | 76/100 | 68/100 |
```

### Ranking Criteria

**Primary Factors (weighted):**
1. Global Score (40%)
2. Risk:Reward Ratio (25%)
3. Setup Quality (20%)
4. Portfolio Fit (15%)

**Secondary Factors (tiebreaker):**
- Volume/liquidity
- ATR (prefer lower volatility)
- Time to target (shorter preferred)
- Historical win rate for this setup type

## Recommendation Matrix

| Score | R:R | Recommendation | Position Size |
|-------|-----|----------------|---------------|
| ≥ 85 | ≥ 3:1 | A+ (Execute immediately) | Full (100%) |
| ≥ 80 | ≥ 2.5:1 | A (Execute) | Full (100%) |
| 70-79 | ≥ 2:1 | B (Execute with confirmation) | Standard (80%) |
| 60-69 | ≥ 1.5:1 | C (Paper trade first) | Reduced (50%) |
| < 60 | Any | D (Skip) | None |

## Scenario Analysis

**When portfolio has room for only 1 position:**
```
⚠️  Portfolio constraint: Max 1 new position

Recommendation: Trade RELIANCE (Rank #1)
Reasoning:
- Highest composite score (87)
- Best R:R ratio (3.2:1)
- Strong HTF alignment
- Excellent risk profile

Alternative: If RELIANCE entry missed, trade TCS (Rank #2)
```

**When multiple positions possible:**
```
💡 Portfolio allows 3 concurrent positions (currently 1 open)

Primary Recommendation: RELIANCE (Score: 87)
  → Full position size

Secondary Options: 
  → TCS (Score: 82) - Full size
  → SBIN (Score: 76) - Reduced size or watch

Avoid: HDFCBANK (Score: 68) - Below threshold
```

## Correlation Check

**Check for correlated symbols:**
```markdown
## Correlation Analysis

| Pair | Correlation | Impact |
|------|-------------|--------|
| RELIANCE ↔ TCS | 0.72 | ⚠️ High - Consider one only |
| SBIN ↔ HDFCBANK | 0.85 | ⚠️ Very High - Pick one |

Recommendation:
- Choose RELIANCE over TCS (better score)
- Choose SBIN over HDFCBANK (better score)
- Diversified portfolio: RELIANCE + SBIN only
```

## Output Format

**Console Output:**
```
╔════════════════════════════════════════════════════════════╗
║         TRADE SETUP COMPARISON (4 setups analyzed)         ║
╠════════════════════════════════════════════════════════════╣
║ 🥇 #1 RELIANCE | BUY | 87/100 | R:R 3.2 | EXECUTE         ║
║ 🥈 #2 TCS      | SELL| 82/100 | R:R 2.8 | EXECUTE          ║
║ 🥉 #3 SBIN     | BUY | 76/100 | R:R 2.5 | PAPER/REDUCED   ║
║ #4 HDFCBANK    | SELL| 68/100 | R:R 1.9 | SKIP              ║
╚════════════════════════════════════════════════════════════╝

Correlation Alert: RELIANCE-TCS correlation 0.72
→ Trade only one for diversification

Recommended: Execute RELIANCE (top ranked, uncorrelated)
```

**Report File:** `reports/{###}-compare-{YYYYMMDD}.md`

## CLI Usage

```bash
# Compare symbols
python -m cli.main compare RELIANCE TCS SBIN

# Compare with auto-evaluation
python -m cli.main compare --symbols "RELIANCE BUY, TCS SELL"

# Compare specific setups
python -m cli.main compare --file setups.json

# Top N only
python -m cli.main compare NIFTY50 --top 5
```

## Comparison Best Practices

### Do:
- Compare minimum 2, maximum 5-7 setups
- Always check correlation between top candidates
- Consider portfolio fit (current exposure)
- Verify liquidity for all candidates
- Check market session timing

### Don't:
- Force comparison if only one good setup exists
- Ignore correlation risk
- Select lower score due to "feeling"
- Overlook R:R ratio differences
- Skip evaluation even for comparison

## Advanced Comparison

**Multi-factor ranking:**
```python
composite_score = (
    af_score * 0.40 +
    rr_normalized * 0.25 +
    setup_quality * 0.20 +
    portfolio_fit * 0.15
)
```

**Portfolio fit calculation:**
```python
# Prefer setups that:
# 1. Don't increase sector concentration
# 2. Add diversification
# 3. Fit within risk limits

portfolio_fit = 1.0
if same_sector_as_existing:
    portfolio_fit -= 0.3
if exceeds_heat_limit:
    portfolio_fit -= 0.5
if optimal_position_size_fits:
    portfolio_fit += 0.2
```
