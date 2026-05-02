# Mode: strategy — Strategy Management

Manage trading strategies — list, enable, disable, configure, and test.

## Strategy Directory

**Location:** `strategies/`

**Available Strategies:**
```
strategies/
├── base.py              # Base strategy class
├── smart_money.py       # SMC (FVG, OB, Liquidity)
├── pattern_detector.py  # Chart patterns
├── mean_reversion.py    # RSI, Bollinger Bands
├── trend_following.py   # Moving averages, ADX
├── fvg_detector.py      # Fair Value Gaps
├── order_block.py       # Order Blocks
├── liquidity.py         # Liquidity analysis
├── scanner.py           # Multi-symbol scanning
└── signal_scorer.py     # Signal quality scoring
```

## Strategy Management Commands

### List Strategies

**Command:**
```bash
python -m cli.main strategy --list
```

**Output:**
```
╔════════════════════════════════════════════════════════════╗
║                   AVAILABLE STRATEGIES                       ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║ 1. Smart Money Concepts (smc)                            🟢 ║
║    └── Type: SMC | Timeframe: 5m/15m | Status: ENABLED   ║
║                                                            ║
║ 2. Pattern Detector (patterns)                           🟢 ║
║    └── Type: Pattern | Timeframe: D/4h | Status: ENABLED  ║
║                                                            ║
║ 3. Mean Reversion (meanrev)                              🔴 ║
║    └── Type: Indicator | Timeframe: 15m | Status: DISABLED║
║                                                            ║
║ 4. Trend Following (trend)                               🟡 ║
║    └── Type: Trend | Timeframe: 1h/D | Status: PAUSED    ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

### Enable/Disable Strategy

**Enable:**
```bash
python -m cli.main strategy --enable smc
```

**Disable:**
```bash
python -m cli.main strategy --disable meanrev
```

### View Strategy Configuration

**Command:**
```bash
python -m cli.main strategy --config smc
```

**Output:**
```
Strategy Configuration: Smart Money Concepts
═══════════════════════════════════════════════════════════

Status: ENABLED
Priority: 1 (highest)

Parameters:
├── Timeframes:
│   ├── LTF (Entry): 5m
│   └── HTF (Bias): 15m
├── Minimum Score: 70
├── Require HTF Alignment: Yes
├── Require FVG: No
├── Require MSS: Yes
├── Min Volume Ratio: 1.2x
└── Max Spread %: 0.5%

Risk Settings:
├── Default R:R: 3:1
├── Min R:R: 2:1
├── Position Size: 2% risk
└── Max Daily Trades: 5

Performance (Last 30 Days):
├── Trades: 24
├── Win Rate: 62.5%
├── Avg R: +1.8R
├── Profit Factor: 2.1
└── Grade: A
```

### Edit Strategy Configuration

**Interactive:**
```bash
python -m cli.main strategy --edit smc
```

**Direct parameter update:**
```bash
python -m cli.main strategy --set smc min_score=75
python -m cli.main strategy --set smc max_positions=3
```

### Strategy Performance

**Command:**
```bash
python -m cli.main strategy --performance smc
```

**Full Report:**
```
Strategy Performance Report: Smart Money Concepts
═══════════════════════════════════════════════════════════

Period: Last 30 Days
Trades: 24

Performance Summary:
├── Win Rate: 62.5% (15W / 9L)
├── Gross Profit: +₹45,600
├── Gross Loss: -₹18,200
├── Net P&L: +₹27,400
├── Profit Factor: 2.51
├── Avg Win: +₹3,040
├── Avg Loss: -₹2,022
├── Win/Loss Ratio: 1.50
├── Expectancy: +₹1,142 per trade
└── Sharpe Ratio: 2.3

R-Multiple Analysis:
├── Avg R: +1.8R
├── Max R: +4.2R
├── Min R: -1.0R
└── R Distribution: [chart]

Trade Distribution:
├── By Day: [heatmap]
├── By Hour: [heatmap]
└── By Symbol: [chart]

Setup Quality Correlation:
├── Score ≥ 80: 80% WR
├── Score 70-79: 58% WR
└── Score < 70: 33% WR
```

### Test Strategy

**Backtest on recent data:**
```bash
python -m cli.main strategy --test smc --days 30
```

**Forward test (paper trading):**
```bash
python -m cli.main strategy --paper-test smc --days 7
```

**Single symbol test:**
```bash
python -m cli.main strategy --test smc --symbol NSE:RELIANCE-EQ
```

## Strategy Configuration File

**Location:** `config/strategies.yml`

```yaml
strategies:
  smc:
    enabled: true
    priority: 1
    timeframes:
      ltf: "5m"
      htf: "15m"
    parameters:
      min_score: 70
      require_htf_alignment: true
      require_fvg: false
      require_mss: true
      min_volume_ratio: 1.2
      max_spread_pct: 0.5
    risk:
      default_rr: 3.0
      min_rr: 2.0
      risk_per_trade: 0.02
      max_daily_trades: 5
    symbols:
      - "NSE:NIFTY50-INDEX"
      - "NSE:BANKNIFTY-INDEX"
      - "NSE:RELIANCE-EQ"
      - "NSE:TCS-EQ"
      
  patterns:
    enabled: true
    priority: 2
    timeframes:
      primary: "D"
      confirmation: "4h"
    parameters:
      min_pattern_bars: 15
      min_confidence: 0.7
      require_volume_breakout: true
    risk:
      default_rr: 2.5
      risk_per_trade: 0.015
      max_daily_trades: 3
    symbols:
      - "NSE:NIFTY50-INDEX"
      - "NSE:BANKNIFTY-INDEX"
```

## Strategy Development

### Create New Strategy

**From template:**
```bash
python -m cli.main strategy --create my_strategy --template smc
```

**Generated file:** `strategies/my_strategy.py`

**Template structure:**
```python
"""
My Custom Strategy

Description of strategy logic.
"""

from strategies.base import BaseStrategy

class MyStrategy(BaseStrategy):
    """Custom trading strategy."""
    
    name = "my_strategy"
    description = "My custom trading strategy"
    
    def __init__(self, config=None):
        super().__init__(config)
        self.min_score = config.get('min_score', 70)
        
    def analyze(self, data):
        """
        Analyze market data and generate signal.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            dict: Signal data with score
        """
        signal = {
            'action': 'HOLD',
            'score': 0,
            'reasoning': '',
            'indicators': {}
        }
        
        # Your strategy logic here
        
        return signal
    
    def validate_setup(self, signal):
        """Validate signal quality."""
        return signal['score'] >= self.min_score
```

### Strategy Validation

**Syntax check:**
```bash
python -m cli.main strategy --validate my_strategy
```

**Logic test:**
```bash
python -m cli.main strategy --test-logic my_strategy
```

## Strategy Priority System

**Priority levels:**
1. Highest priority - Executed first
2. Normal priority
3. Low priority - Confirmation only

**Conflict resolution:**
```
Signal Conflicts:
├── SMC: BUY (Score: 85)
├── Patterns: SELL (Score: 72)
└── Resolution: Execute BUY (higher score)

Same Symbol, Same Direction:
├── SMC: BUY (Score: 80, Priority: 1)
└── Patterns: BUY (Score: 75, Priority: 2)
└── Resolution: Execute SMC only (priority)
```

## Strategy Combinations

**Multi-strategy mode:**
```yaml
strategy_mode: "combined"  # Options: single, combined, consensus

# Single: Use highest priority only
# Combined: Use all, filter by score
# Consensus: Require 2+ strategies to agree
```

**Consensus example:**
```
Consensus Required: 2 strategies minimum

RELIANCE Analysis:
├── SMC: BUY (85)
├── Patterns: BUY (78)
├── MeanRev: NEUTRAL (45)
└── Consensus: BUY (2 strategies agree)
→ Signal strength: STRONG
```

## Strategy Alerts

**Notify on:**
- Strategy enabled/disabled
- Strategy parameter changed
- Strategy performance drops below threshold
- Strategy enters/exits drawdown

## Best Practices

### Strategy Selection
- [ ] Test thoroughly in paper mode first
- [ ] Run minimum 50 trades before live
- [ ] Monitor correlation with existing strategies
- [ ] Review performance weekly
- [ ] Disable underperformers quickly

### Parameter Optimization
- [ ] Use walk-forward analysis
- [ ] Don't over-optimize (curve fitting)
- [ ] Test on out-of-sample data
- [ ] Validate with paper trading
- [ ] Make small, incremental changes

### Risk Management
- [ ] Set max trades per strategy per day
- [ ] Limit strategy correlation
- [ ] Monitor strategy-level drawdown
- [ ] Have kill switch ready
