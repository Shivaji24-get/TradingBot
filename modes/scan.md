# Mode: scan — Market Scanning for Opportunities

Execute systematic market scanning to discover trading opportunities.

## Scan Configuration

Load from `config/trading_profile.yml`:
- symbols_to_scan: list or index group
- timeframes: [5m, 15m, 1h, D]
- strategies: which to enable (SMC, patterns, mean reversion)
- min_score_threshold: default 60
- auto_trade_enabled: yes/no
- auto_trade_threshold: min score for auto-trade (default 75)

## Scan Process

### Step 1: Load Scanner
```python
from strategies import StockScanner
scanner = StockScanner(
    enable_smc=True,
    enable_patterns=True,
    enable_scoring=True
)
```

### Step 2: Scan Symbols

**For each symbol in scan list:**

1. **Fetch Market Data**
   - Load candles for primary timeframe
   - Load HTF candles for bias
   - Get current quote

2. **Apply Enabled Strategies**
   
   **SMC Scan:**
   - Check HTF structure
   - Identify liquidity zones
   - Detect sweeps
   - Check for MSS
   - Locate FVGs and OBs
   - Calculate SMC score
   
   **Pattern Scan:**
   - Detect chart patterns
   - Measure pattern quality
   - Calculate pattern confidence
   
   **Indicator Scan:**
   - Calculate RSI
   - Check SMA relationships
   - Volume analysis
   - Generate composite score

3. **Calculate Signal Score**
   - Combine strategy scores
   - Apply confluence bonus
   - Generate final 0-100 score

4. **Filter Results**
   - Keep signals ≥ min_score_threshold
   - Sort by score descending

### Step 3: Display Results

**Table Format:**
```
| Rank | Symbol | Signal | Score | Price | HTF | Sweep | MSS | FVG | Pattern |
|------|--------|--------|-------|-------|-----|-------|-----|-----|---------|
```

**Color Coding:**
- Score ≥ 75: Green (STRONG)
- Score 60-74: Yellow (MODERATE)
- Score 50-59: Orange (WEAK)
- Score < 50: Red (SKIP)

### Step 4: Optional Auto-Trade

If auto_trade_enabled and signal ≥ auto_trade_threshold:
1. Run full A-F evaluation
2. Validate risk parameters
3. Place paper or live order (per config)
4. Log to tracker

## Zero-Token Scanner

For efficient scanning without LLM costs:

```bash
python -m cli.main scan --index NIFTY50 --timeframe 5m
python -m cli.main scan --symbols "NSE:RELIANCE-EQ,NSE:TCS-EQ" --smc
```

## Scan History

Maintain deduplication in `data/scan-history.tsv`:
```
date	symbol	signal	score	notes
```

Check for:
- Same symbol + similar signal within 24 hours → skip duplicate
- Reposting detection: same signal recurring 3+ times → flag as stale

## Output

**Console Output:**
- Summary: X symbols scanned, Y signals found, Z strong (≥75%)
- Top N results table
- Legend for symbols

**File Output:**
- Save detailed results to `output/scan-{YYYYMMDD-HHMM}.json`
- Summary to `data/scan-history.tsv`

## Scanner Commands

| Command | Description |
|---------|-------------|
| `scan --index NIFTY50` | Scan NIFTY50 stocks |
| `scan --index BANKNIFTY --smc` | SMC scan on bank stocks |
| `scan --live --auto-trade` | Live scanning with auto-trade |
| `scan --symbol NSE:SBIN-EQ` | Scan single symbol |

## Best Practices

1. **Scan frequency:** Every 5-15 minutes during market hours
2. **Symbol coverage:** Focus on liquid, preferred symbols
3. **Avoid scans:** During high volatility news events
4. **Post-scan:** Always review top signals with A-F evaluation before trading
