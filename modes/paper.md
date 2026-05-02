# Mode: paper — Paper Trading Simulation

Execute paper trading mode for safe strategy testing without real money.

## Paper Trading Overview

**Purpose:**
- Test strategies without financial risk
- Validate signal quality
- Practice execution discipline
- Build confidence before live trading

**How It Works:**
- Simulated trades with virtual capital
- Same signals and logic as live trading
- Real market prices from API
- Tracks virtual P&L
- Generates same reports as live trading

## Configuration

**In trading_profile.yml:**
```yaml
paper_trading:
  enabled: true
  initial_capital: 100000  # ₹1 Lakh virtual
  risk_per_trade: 0.01     # Same as live settings
  commission_per_trade: 20  # Simulate real costs
  slippage: 0.001         # 0.1% slippage
  
  # Auto-promotion settings
  auto_promote:
    enabled: true
    min_trades: 20
    min_win_rate: 0.55
    min_profit_factor: 1.5
    max_drawdown: 0.10
```

## Paper Trading Session

### Session Start

```
╔══════════════════════════════════════════════════════════════╗
║              📘 PAPER TRADING SESSION STARTED                ║
╠══════════════════════════════════════════════════════════════╣
║ Virtual Capital: ₹{X}                                        ║
║ Risk/Trade:    {X}%                                         ║
║ Commission:    ₹{X} per trade                               ║
║ Slippage:      {X}%                                         ║
╚══════════════════════════════════════════════════════════════╝

⚠️  All trades are SIMULATED. No real money at risk.
   Performance here does not guarantee live results.
```

### Trade Simulation

**When signal generated:**
```
[SIGNAL] NSE:RELIANCE-EQ BUY @ ₹2,450 (Score: 82)
[PAPER]  Simulating entry...
[PAPER]  Entry fill: ₹2,452 (slippage: ₹2)
[PAPER]  Position opened: 40 shares
[PAPER]  Stop set: ₹2,420
[PAPER]  Virtual risk: ₹1,280
```

**When exit triggered:**
```
[EXIT] Stop triggered for RELIANCE @ ₹2,420
[PAPER] Simulating exit...
[PAPER] Exit fill: ₹2,418 (slippage: ₹2)
[PAPER] P&L: -₹1,360 (commission: ₹40)
[PAPER] Virtual capital: ₹98,600
```

## Paper vs Live Differences

| Aspect | Paper Trading | Live Trading |
|--------|--------------|--------------|
| Capital | Virtual | Real |
| Orders | Simulated | Real broker orders |
| Slippage | Estimated | Actual market |
| Emotions | Lower | Higher |
| Execution | Instant | Market dependent |
| Costs | Estimated | Actual |

**Important:** Paper results are typically BETTER than live because:
- No emotional pressure
- Perfect fills (no partial fills)
- No market impact
- No connection delays

**Expect live performance to be 10-20% worse.**

## Paper Trading Reports

**Daily Summary:**
```
📊 Paper Trading Summary - 2026-01-15

Virtual P&L: +₹3,450 (+3.45%)
Trades: 5
Win Rate: 60% (3W / 2L)
Commissions: ₹200
Net P&L: +₹3,250

Virtual Capital: ₹103,250

Comparison to Live (if applicable):
Paper: +3.45% | Live: +2.80%
```

**Saved to:** `data/paper-trades.md`

## Performance Tracking

**Paper Trading Metrics:**
- Virtual P&L
- Win/Loss ratio
- Profit factor
- Max drawdown
- R-multiple distribution
- Strategy performance by type

**Progress to Live:**
```
Paper Trading Progress
═══════════════════════════════════════════════════════════

Requirements for Live Trading:
├── Min Trades:     20 / 20 ✓
├── Min Win Rate:   58% / 55% ✓
├── Min PF:         1.8 / 1.5 ✓
├── Max Drawdown:   8% / 10% ✓
└── Consistency:    14 days / 14 days ✓

✅ READY FOR LIVE TRADING

Recommendation: Start with 50% position size
for first week of live trading.
```

## Auto-Promotion

**When criteria met:**
```
🎉 PAPER TRADING MILESTONE ACHIEVED

After {X} trades over {X} days:
• Win Rate: {X}%
• Profit Factor: {X}
• Max Drawdown: {X}%

You have met the criteria for live trading!

Options:
1. Continue paper trading
2. Start live trading with reduced size
3. Start live trading with full size
```

## Best Practices

### Do:
- [ ] Treat paper trades seriously (proper sizing, stops)
- [ ] Track emotions even though it's fake money
- [ ] Test all strategies you plan to use live
- [ ] Trade for at least 2-4 weeks
- [ ] Aim for 50+ paper trades before going live

### Don't:
- [ ] Take excessive risk "because it's paper"
- [ ] Skip stop-losses
- [ ] Change strategy after every loss
- [ ] Rush to live trading
- [ ] Expect identical results in live

## CLI Commands

```bash
# Start paper trading
python -m cli.main paper

# Start with custom capital
python -m cli.main paper --capital 500000

# Paper trading status
python -m cli.main paper --status

# Paper trading report
python -m cli.main paper --report --days 30

# Compare paper vs live
python -m cli.main paper --compare

# Reset paper account
python -m cli.main paper --reset
```

## Paper Trading Diary

**Keep notes in modes/_profile.md:**

```markdown
## Paper Trading Notes

### Week 1 (Jan 1-7)
- Trades: 12
- P&L: +₹1,200
- Learned: SMC works best in morning session
- Issues: Overtrading on Friday

### Week 2 (Jan 8-14)
- Trades: 15
- P&L: +₹2,800
- Learned: Adding volume filter improved results
- Ready for live: Next week with reduced size
```

## Limitations

**What paper trading cannot simulate:**
- Emotional pressure of real money
- Connection/API issues
- Broker platform delays
- Market impact of large orders
- Partial fills
- Price rejection at limit orders

**Use paper trading for:**
- Strategy logic validation
- Signal quality assessment
- Risk management practice
- System familiarity

**Not for:**
- Exact P&L prediction
- Emotional preparation
- Execution speed testing
