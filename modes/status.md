# Mode: status — Bot and Portfolio Status

Display comprehensive status of trading bot and portfolio.

## Status Components

### 1. Bot Status

**Running State:**
```
Bot Status: 🟢 RUNNING / 🟡 PAUSED / 🔴 STOPPED
Uptime: {X} hours {X} minutes
Mode: {Paper Trading / Live Trading}
Session: {Session #X}
```

**System Health:**
```
System Health: ✅ HEALTHY / ⚠️ WARNING / ❌ ERROR
├── API Connection: ✅ Connected (latency: {X}ms)
├── Data Feed: ✅ Real-time
├── Database: ✅ Synced
├── Disk Space: ✅ {X}% free
└── Memory: ✅ {X}% used
```

### 2. Market Status

**Current Market:**
```
Market: NSE
Status: 🟢 OPEN / 🔴 CLOSED / 🟡 PRE-MARKET / 🟡 POST-MARKET
Time: {HH:MM} IST
Session: {Regular / Pre / Post}

Nifty 50: {price} ({change}%)
Bank Nifty: {price} ({change}%)
VIX: {value} ({trend})
```

### 3. Portfolio Overview

**Capital Summary:**
```
╔════════════════════════════════════════════════════════════╗
║                   PORTFOLIO SUMMARY                        ║
╠════════════════════════════════════════════════════════════╣
║ Starting Capital:     ₹{X}                                 ║
║ Current Value:       ₹{X} ({X}%)                          ║
║ Available Cash:      ₹{X}                                 ║
║ Invested:            ₹{X} ({X}%)                          ║
║ Today's P&L:         ₹{X} ({X}%)                          ║
║ Total P&L:           ₹{X} ({X}%)                          ║
╚════════════════════════════════════════════════════════════╝
```

### 4. Open Positions

**Position Table:**
```markdown
| # | Symbol | Side | Qty | Entry | Current | Stop | Target | P&L | R:R | Status |
|---|--------|------|-----|-------|---------|------|--------|-----|-----|--------|
| 1 | RELIANCE | BUY | 40 | 2450 | 2520 | 2420 | 2600 | +2,800 | +2.8 | 🟢 In Profit |
| 2 | TCS | SELL | 25 | 3850 | 3780 | 3920 | 3600 | +1,750 | +1.0 | 🟢 In Profit |
| 3 | SBIN | BUY | 100 | 650 | 645 | 640 | 675 | -500 | -0.5 | 🔴 Losing |
```

**Position Summary:**
```
Open Positions: 3
Profitable: 2 (₹+4,550)
Losing: 1 (₹-500)
Portfolio Heat: 4.2% / 6% limit
Avg Distance to Stop: 1.8%
```

### 5. Today's Activity

**Trade Summary:**
```
Today's Trades: 5
├── Opened: 3
├── Closed: 2
├── Win Rate: 60% (3W / 2L)
├── Gross P&L: +₹{X}
├── Commissions: -₹{X}
└── Net P&L: +₹{X}
```

**Recent Trades:**
```markdown
| Time | Symbol | Action | Price | Qty | P&L |
|------|--------|--------|-------|-----|-----|
| 10:30 | RELIANCE | Entry | 2450 | 40 | — |
| 11:15 | TCS | Entry | 3850 | 25 | — |
| 12:00 | SBIN | Entry | 650 | 100 | — |
| 13:30 | HDFCBANK | Exit | 1420 | 50 | +850 |
| 14:00 | ICICIBANK | Exit | 1120 | 75 | -320 |
```

### 6. Signal Activity

**Recent Signals:**
```
Last 5 Signals:
├── 14:30 RELIANCE BUY (82/100) → EXECUTED
├── 14:15 TCS SELL (78/100) → EXECUTED
├── 13:45 SBIN BUY (65/100) → EXECUTED
├── 13:00 HDFCBANK SELL (45/100) → SKIPPED
└── 12:30 ICICIBANK BUY (72/100) → EXECUTED

Signals Generated Today: 12
Executed: 8 | Skipped: 4
Avg Score: 71/100
```

### 7. Strategy Performance

**Active Strategies:**
```
Strategy Performance (Today):
├── SMC: 4 trades, 75% WR, +₹2,800
├── Patterns: 3 trades, 66% WR, +₹1,200
├── Mean Reversion: 2 trades, 50% WR, -₹450
└── Overall: 60% WR, +₹3,550
```

### 8. Risk Metrics

**Current Risk Status:**
```
Risk Dashboard:
├── Portfolio Heat: 4.2% / 6% ✅
├── Daily P&L: +2.8% / 3% limit ✅
├── Max Position: 15% / 20% limit ✅
├── Consecutive Losses: 1 / 3 limit ✅
├── Correlated Positions: 0 ✅
└── Overall Risk: MODERATE ✅

⚠️  Watch: SBIN approaching stop (-0.5R)
```

## Status Views

### Compact View
```
[STATUS] Bot: RUNNING | Market: OPEN | P&L Today: +2.8% | Positions: 3
```

### Standard View
Full sections 1-4 above.

### Detailed View
All sections 1-8 with additional metrics:
- Per-position unrealized P&L chart
- Time in trade for each position
- Upcoming events (earnings, etc.)
- Pending orders

### JSON Output (for automation)
```json
{
  "bot": {
    "status": "running",
    "uptime_seconds": 14400,
    "mode": "paper"
  },
  "market": {
    "status": "open",
    "nifty": 22450,
    "change": 0.75
  },
  "portfolio": {
    "capital": 100000,
    "value": 104500,
    "cash": 45000,
    "pnl_today": 2800,
    "pnl_pct": 2.8
  },
  "positions": {
    "count": 3,
    "open": [...],
    "heat": 4.2
  }
}
```

## CLI Commands

```bash
# Standard status
python -m cli.main status

# Compact status
python -m cli.main status --compact

# Detailed status
python -m cli.main status --detailed

# JSON output
python -m cli.main status --json

# Specific component
python -m cli.main status --positions
python -m cli.main status --risk
python -m cli.main status --today

# Refresh interval (live view)
python -m cli.main status --watch --interval 30
```

## Auto-Refresh Status

**Live dashboard mode:**
```bash
python -m cli.main status --watch
```

Updates every 30 seconds with:
- Flashing updates on changes
- Color coding for P&L
- Sound alert on significant events (optional)

## Status Alerts

**When status changes:**
- Position closed (P&L update)
- New position opened
- Stop loss approached (< 50% distance)
- Target approached (> 80% distance)
- Daily loss limit approaching
- Portfolio heat warning
- Market closing soon

## File Locations

**Status reads from:**
- `data/positions.md` — Open positions
- `data/trades.md` — Trade history
- `data/signals.md` — Signal log
- `config/trading_profile.yml` — Settings

## Error Handling

**If data files missing:**
```
⚠️  Warning: positions.md not found
→ Creating empty positions file
→ No open positions to display
```

**If API connection lost:**
```
❌ Error: Cannot connect to broker API
→ Showing last known data (5 minutes old)
→ Retry in 30 seconds...
```
