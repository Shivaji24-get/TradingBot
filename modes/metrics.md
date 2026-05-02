# Mode: metrics — Performance Analytics

Comprehensive performance analytics and metrics dashboard.

## Metric Categories

### 1. Return Metrics

**Basic Returns:**
```
╔════════════════════════════════════════════════════════════╗
║                    RETURN METRICS                          ║
╠════════════════════════════════════════════════════════════╣
║ Total Return:        +₹{X} (+{X}%)                          ║
║ Annualized Return:  +{X}%                                  ║
║ Daily Avg Return:   +{X}%                                  ║
║ Weekly Avg Return:   +{X}%                                  ║
║ Monthly Return:      +{X}%                                   ║
║ YTD Return:         +{X}%                                  ║
╚════════════════════════════════════════════════════════════╝
```

**Return Distribution:**
```
Return Distribution (Daily):
├── > +5%:   ██ (2 days)
├── +2-5%:   ████████ (8 days)
├── +0-2%:   ████████████████████ (20 days)
├── 0%:      ████████████ (12 days)
├── -0-2%:   ██████████ (10 days)
├── -2-5%:   █████ (5 days)
└── < -5%:   █ (1 day)

Best Day:   +{X}% ({date})
Worst Day:  -{X}% ({date})
```

### 2. Risk Metrics

**Risk Analysis:**
```
╔════════════════════════════════════════════════════════════╗
║                     RISK METRICS                           ║
╠════════════════════════════════════════════════════════════╣
║ Volatility (σ):     {X}%                                   ║
║ Max Drawdown:       -{X}%                                  ║
║ Current Drawdown:   -{X}%                                  ║
║ Downside Dev:       {X}%                                   ║
║ VaR (95%):          -{X}%                                  ║
║ CVaR (95%):         -{X}%                                  ║
╚════════════════════════════════════════════════════════════╝
```

**Drawdown Analysis:**
```
Major Drawdowns:
| # | Peak | Trough | DD % | Days | Recovery |
|---|------|--------|------|------|----------|
| 1 | ₹{X} | ₹{X} | -{X}% | {X} | {X} days |
| 2 | ₹{X} | ₹{X} | -{X}% | {X} | {X} days |

Average Drawdown: -{X}%
Average Recovery: {X} days
```

### 3. Trade Metrics

**Trade Statistics:**
```
╔════════════════════════════════════════════════════════════╗
║                    TRADE METRICS                           ║
╠════════════════════════════════════════════════════════════╣
║ Total Trades:       {X}                                    ║
║ Win Rate:           {X}% ({X}W / {X}L)                     ║
║ Profit Factor:      {X}                                    ║
║ Avg Win:           +₹{X}                                   ║
║ Avg Loss:          -₹{X}                                   ║
║ Win/Loss Ratio:     {X}:1                                  ║
║ Expectancy:        +₹{X} per trade                         ║
╚════════════════════════════════════════════════════════════╝
```

**R-Multiple Distribution:**
```
R-Multiple Distribution:
├── > +3R:   █████ (10 trades, avg +4.2R)
├── +1-3R:   ████████████████ (32 trades, avg +1.8R)
├── 0-1R:    ████████ (16 trades)
├── 0R:      ████ (8 trades, breakeven)
├── -1-0R:   ██████ (12 trades)
└── > -1R:   ██ (4 trades, avg -1.5R)

Average R: +{X}R per trade
```

### 4. Time-Based Analysis

**Performance by Time:**
```
Performance by Session:
├── Pre-market (9:00-9:15):  +{X}% | {X} trades
├── Opening (9:15-10:30):    +{X}% | {X} trades ⭐ Best
├── Mid-day (10:30-14:00):  +{X}% | {X} trades
├── Closing (14:00-15:30):  +{X}% | {X} trades
└── Post-market:            +{X}% | {X} trades

Performance by Day:
├── Monday:     +{X}% | {X} trades
├── Tuesday:    +{X}% | {X} trades
├── Wednesday:  +{X}% | {X} trades ⭐ Best
├── Thursday:   +{X}% | {X} trades
└── Friday:     +{X}% | {X} trades
```

### 5. Strategy Performance

**Strategy Comparison:**
```
╔════════════════════════════════════════════════════════════╗
║                  STRATEGY PERFORMANCE                      ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║ SMC (Smart Money)                                         ║
├── Trades: {X} | Win Rate: {X}% | P&L: +₹{X}              ║
├── Avg R: +{X} | Profit Factor: {X} | Sharpe: {X}          ║
└── Grade: A                                                ║
║                                                            ║
║ Pattern Breakouts                                         ║
├── Trades: {X} | Win Rate: {X}% | P&L: +₹{X}              ║
├── Avg R: +{X} | Profit Factor: {X} | Sharpe: {X}          ║
└── Grade: B+                                               ║
║                                                            ║
║ Mean Reversion                                            ║
├── Trades: {X} | Win Rate: {X}% | P&L: -₹{X}              ║
├── Avg R: +{X} | Profit Factor: {X} | Sharpe: {X}          ║
└── Grade: C ⚠️ Underperforming                              ║
╚════════════════════════════════════════════════════════════╝
```

### 6. Quality Metrics

**Signal Quality Analysis:**
```
Performance by Signal Score:
├── ≥ 85 (Strong):     {X} trades, {X}% WR, +₹{X} | Grade: A
├── 70-84 (Good):      {X} trades, {X}% WR, +₹{X} | Grade: B
├── 60-69 (Moderate):  {X} trades, {X}% WR, +₹{X} | Grade: C
└── < 60 (Weak):       {X} trades, {X}% WR, -₹{X} | Skip these

Recommendation: Only trade signals ≥ 70
```

**Setup Quality Impact:**
```
Performance by Setup Component:
├── HTF Aligned:    {X}% WR vs {X}% (not aligned)
├── Volume Conf:    {X}% WR vs {X}% (low volume)
├── SMC Confluence: {X}% WR vs {X}% (no SMC)
└── Pattern Conf:   {X}% WR vs {X}% (no pattern)
```

### 7. Efficiency Metrics

**Trading Efficiency:**
```
╔════════════════════════════════════════════════════════════╗
║                   EFFICIENCY METRICS                       ║
╠════════════════════════════════════════════════════════════╣
║ Signals Generated:    {X}                                  ║
║ Trades Executed:      {X} ({X}% of signals)              ║
║ Average Hold Time:    {X} hours                           ║
║ Time to Target:       {X}% avg                            ║
║ Time to Stop:         {X}% avg                            ║
║ Breakeven Trades:     {X}%                                ║
║ Early Exits:         {X} (manual)                         ║
╚════════════════════════════════════════════════════════════╝
```

**Cost Analysis:**
```
Trading Costs:
├── Commissions:     ₹{X} ({X}% of gross P&L)
├── Slippage:        ₹{X} ({X}% of gross P&L)
├── Total Costs:     ₹{X} ({X}% of gross P&L)
└── Cost per Trade:  ₹{X}

Impact on Returns: -{X}%
```

### 8. Benchmark Comparison

**Market Comparison:**
```
Performance vs Benchmarks:
                    You     Nifty   BankNifty
Total Return:       +{X}%    +{X}%   +{X}%
Annualized:         {X}%    {X}%    {X}%
Sharpe Ratio:       {X}     {X}     {X}
Max DD:            -{X}%   -{X}%   -{X}%

Alpha vs Nifty:     +{X}%
Beta vs Nifty:      {X}
Correlation:        {X}
```

## Advanced Metrics

### Kelly Criterion
```
Kelly Analysis:
├── Win Rate: {X}%
├── Avg Win: ₹{X}
├── Avg Loss: ₹{X}
├── Edge: {X}%
├── Kelly %: {X}% (optimal position size)
├── Half Kelly: {X}% (recommended)
└── Current: {X}% vs Half Kelly
```

### Monte Carlo Simulation
```
Monte Carlo Results (10,000 runs):
├── Probability of Profit: {X}%
├── Probability of >50% DD: {X}%
├── Expected Max DD: -{X}%
├── Median Return: +{X}%
├── Worst Case (5%): -{X}%
└── Best Case (95%): +{X}%
```

### Consecutive Analysis
```
Streak Analysis:
├── Max Consecutive Wins: {X} (occurred: {date})
├── Max Consecutive Losses: {X} (occurred: {date})
├── Current Streak: {X} {wins/losses}
├── Avg Win Streak: {X}
└── Avg Loss Streak: {X}
```

## Report Generation

**Daily Report:**
```bash
python scripts/daily_report.py
```
Output: `reports/daily-metrics-{YYYYMMDD}.md`

**Monthly Report:**
```bash
python -m cli.main metrics --report monthly
```

**Custom Period:**
```bash
python -m cli.main metrics --from 2026-01-01 --to 2026-01-31
```

## CLI Commands

```bash
# Show all metrics
python -m cli.main metrics

# Specific metric category
python -m cli.main metrics --category returns
python -m cli.main metrics --category risk
python -m cli.main metrics --category trades

# Export data
python -m cli.main metrics --export csv
python -m cli.main metrics --export json

# Compare periods
python -m cli.main metrics --compare last_month

# Strategy breakdown
python -m cli.main metrics --by-strategy

# Symbol breakdown
python -m cli.main metrics --by-symbol
```

## Visualization

**If matplotlib available:**
- Equity curve chart
- Drawdown chart
- Monthly returns heatmap
- Win/loss distribution
- R-multiple histogram

**Output:** `output/metrics-charts-{date}.png`

## Benchmark Grades

| Metric | A Grade | B Grade | C Grade | D Grade |
|--------|---------|---------|---------|---------|
| Sharpe Ratio | > 2.0 | 1.0-2.0 | 0.5-1.0 | < 0.5 |
| Win Rate | > 60% | 50-60% | 40-50% | < 40% |
| Profit Factor | > 2.0 | 1.5-2.0 | 1.0-1.5 | < 1.0 |
| Max DD | < 10% | 10-20% | 20-30% | > 30% |
| Recovery | < 1 month | 1-3 months | 3-6 months | > 6 months |
