# Mode: backtest — Strategy Backtesting

Execute comprehensive backtest on a trading strategy with historical data.

## Backtest Configuration

**Required Parameters:**
- Strategy name (from strategies/)
- Date range (start, end)
- Symbols to test
- Timeframe

**Optional Parameters:**
- Initial capital (default: ₹100,000)
- Position sizing method (default: risk-based 1%)
- Commission per trade
- Slippage estimate

## Backtest Process

### Step 1: Load Configuration

From arguments or config:
```yaml
backtest:
  strategy: "smart_money"
  symbols: ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"]
  start_date: "2025-06-01"
  end_date: "2025-12-31"
  timeframe: "5m"
  initial_capital: 100000
  risk_per_trade: 0.01
  commission: 20  # per trade
  slippage: 0.001  # 0.1%
```

### Step 2: Load Historical Data

For each symbol in test period:
- Load OHLCV candles
- Handle gaps/missing data
- Adjust for corporate actions (stocks)

### Step 3: Strategy Initialization

```python
from strategies import strategy_loader

strategy = strategy_loader.load(config['strategy'])
strategy.set_parameters(config.get('parameters', {}))
```

### Step 4: Simulation Loop

**For each candle in chronological order:**

1. Update indicators and patterns
2. Generate signals
3. Check for existing positions:
   - Evaluate exit conditions
   - Update stop-loss (if trailing)
   - Record unrealized P&L

4. For new signals:
   - Validate signal quality
   - Calculate position size
   - Check risk limits
   - Simulate entry (with slippage)
   - Record trade open

5. End of day processing:
   - Mark-to-market positions
   - Check for time-based exits

### Step 5: Calculate Metrics

**Return Metrics:**
- Total Return: % gain/loss
- Annualized Return: CAGR
- Volatility: Std dev of returns

**Risk Metrics:**
- Sharpe Ratio: (Return - Risk Free) / Volatility
- Sortino Ratio: (Return - RF) / Downside Vol
- Maximum Drawdown: Peak to trough decline
- Calmar Ratio: CAGR / Max Drawdown

**Trade Metrics:**
- Total Trades
- Win Rate: % winning trades
- Profit Factor: Gross Profit / Gross Loss
- Average Win: Mean winning trade
- Average Loss: Mean losing trade
- Win/Loss Ratio: Avg Win / Avg Loss
- Expectancy: (Win% × Avg Win) - (Loss% × Avg Loss)

**Advanced Metrics:**
- Consecutive Wins/Losses (max)
- Recovery Factor: Net Profit / Max Drawdown
- R-Multiple Distribution
- Payoff Ratio

### Step 6: Generate Report

```markdown
# Backtest Report: {Strategy}

**Period:** {start_date} to {end_date}
**Symbols:** {list}
**Timeframe:** {timeframe}
**Initial Capital:** ₹{initial}

---

## Performance Summary

| Metric | Value |
|--------|-------|
| Final Capital | ₹{X} |
| Total Return | {X}% |
| Annualized Return | {X}% |
| Max Drawdown | {X}% |
| Sharpe Ratio | {X} |
| Sortino Ratio | {X} |

## Trade Statistics

| Metric | Value |
|--------|-------|
| Total Trades | {X} |
| Winning Trades | {X} ({X}%) |
| Losing Trades | {X} ({X}%) |
| Avg Win | ₹{X} |
| Avg Loss | ₹{X} |
| Win/Loss Ratio | {X}:1 |
| Profit Factor | {X} |
| Expectancy | ₹{X} per trade |

## Monthly Returns

| Month | Return | Cumulative |
|-------|--------|------------|
| {Month} | {X}% | {X}% |

## Equity Curve
[ASCII or reference to chart file]

## Drawdown Analysis

| Drawdown | Start | End | Duration | Recovery |
|----------|-------|-----|----------|----------|
| {X}% | {date} | {date} | {X} days | {X} days |

## Strategy-Specific Analysis

### Signal Distribution
- BUY signals: {X}
- SELL signals: {X}
- HOLD/No signal: {X}

### Score Analysis
- Signals ≥ 80: {X} trades, {X}% win rate
- Signals 60-79: {X} trades, {X}% win rate
- Signals < 60: {X} trades, {X}% win rate

## Conclusions
- Strengths identified
- Weaknesses identified
- Recommendations for optimization

---
**Generated:** {timestamp}
**Data Quality:** {X}% complete
```

## Output Files

1. **Report:** `reports/{###}-{strategy}-{date}-backtest.md`
2. **Trade Log:** `output/backtest-{strategy}-{date}-trades.csv`
3. **Equity Curve:** `output/backtest-{strategy}-{date}-equity.csv`
4. **Charts:** `output/backtest-{strategy}-{date}-charts.png` (if matplotlib available)

## Backtest Best Practices

1. **Out-of-Sample Testing**
   - Use 70% in-sample for optimization
   - Test on 30% out-of-sample
   - Report both results

2. **Walk-Forward Analysis**
   - Rolling window optimization
   - More robust than single backtest

3. **Monte Carlo Simulation**
   - Randomize trade order
   - Test robustness

4. **Transaction Costs**
   - Always include realistic commissions
   - Include slippage (especially for market orders)

5. **Limitations Disclosure**
   - Historical ≠ future
   - Survivorship bias (delisted stocks)
   - Look-ahead bias check

## CLI Usage

```bash
# Basic backtest
python -m cli.main backtest --strategy smart_money --start 2025-06-01 --end 2025-12-31

# Multi-symbol backtest
python -m cli.main backtest --strategy pattern --symbols NIFTY50 --timeframe 5m

# With custom capital
python -m cli.main backtest --strategy smc --capital 500000 --risk 0.02
```
