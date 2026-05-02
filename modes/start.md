# Mode: start — Trading Bot Startup

Execute the trading bot startup sequence.

## Pre-Flight Checklist

### 1. Configuration Validation

**Check config/trading_profile.yml exists:**
- [ ] File exists and is readable
- [ ] Required fields present
- [ ] Values within acceptable ranges
- [ ] No syntax errors

**Required Configuration Fields:**
```yaml
# Trading Identity
name: "Trader Name"
experience: "Intermediate"  # Beginner/Intermediate/Advanced
market: "NSE"
account_type: "Retail"

# Risk Parameters
risk_per_trade: 0.01  # 1%
max_portfolio_heat: 0.06  # 6%
max_positions: 5
daily_loss_limit: 0.03  # 3%

# Broker Settings
client_id: "XXXXX"
# secret_key: loaded from env or secure storage

# Trading Preferences
enable_smc: true
enable_patterns: true
paper_trading: true  # Start with paper
```

### 2. Authentication Check

**Verify API access:**
```python
from auth import TokenManager
tm = TokenManager(client_id, secret_key)
token = tm.get_access_token()
if not token:
    raise AuthenticationError("Not logged in. Run 'login' first.")
```

**Test API connection:**
- Fetch account profile
- Get funds information
- Verify market data access

### 3. Market Status Check

**Check if market is open:**
```python
from utils import is_market_open
if not is_market_open():
    logger.info("Market closed. Bot will wait for market open.")
    # Option: Start in "wait mode" or exit
```

**Market Hours (NSE):**
- Pre-market: 9:00 AM - 9:15 AM
- Regular: 9:15 AM - 3:30 PM
- Post-market: 3:40 PM - 4:00 PM

### 4. Data Files Check

**Verify data directory structure:**
```
data/
├── trades.md        ← Creates if missing
├── positions.md     ← Creates if missing
├── signals.md       ← Creates if missing
└── scan-history.tsv ← Creates if missing
```

**Initialize if empty:**
```markdown
# trades.md template
| # | Date | Symbol | Side | Entry | Exit | Qty | P&L | Strategy | Status |
|---|------|--------|------|-------|------|-----|-----|----------|--------|

# positions.md template
| Symbol | Side | Entry | Stop | Target | Qty | Status | Opened | Strategy |
|--------|------|-------|------|--------|-----|--------|--------|----------|

# signals.md template
| # | Date | Symbol | Signal | Score | Status | P&L | Report |
|---|------|--------|--------|-------|--------|-----|--------|
```

### 5. Strategy Loading

**Load and validate strategies:**
```python
from strategies import strategy_loader

strategies = strategy_loader.load_enabled_strategies()
for strategy in strategies:
    strategy.validate()
    logger.info(f"Loaded strategy: {strategy.name}")
```

### 6. Health Check

**Run system health check:**
```bash
python scripts/health_check.py
```

**Verify:**
- [ ] All modules importable
- [ ] Database connections (if any)
- [ ] Disk space available
- [ ] Log directory writable
- [ ] Notification channels configured (if enabled)

## Startup Sequence

### Phase 1: Initialization (0-5 seconds)

```
[STARTUP] Trading Bot v1.0
[STARTUP] Loading configuration... ✓
[STARTUP] Authenticating... ✓
[STARTUP] Checking market status... ✓
[STARTUP] Initializing data files... ✓
[STARTUP] Loading strategies... ✓
[STARTUP] Health check... ✓
```

### Phase 2: Pre-Market Setup (if applicable)

**If starting before market open:**
```
[INFO] Market opens in {X} minutes
[INFO] Running pre-market scan...
[INFO] {X} potential setups identified
[INFO] Waiting for market open...
```

### Phase 3: Trading Loop Start

**If market is open:**
```
[INFO] Market is OPEN
[INFO] Starting trading loop...
[INFO] Monitoring {X} symbols
[INFO] Active strategies: {list}
[INFO] Risk per trade: {X}%
[INFO] Max positions: {X}
```

## Bot Status Display

**Startup complete status:**
```
╔══════════════════════════════════════════════════════════════╗
║                    TRADING BOT ACTIVE                        ║
╠══════════════════════════════════════════════════════════════╣
║ Mode:          {Paper Trading / Live Trading}              ║
║ Capital:       ₹{available} available                        ║
║ Risk/Trade:    {X}%                                         ║
║ Max Positions: {X}                                          ║
║ Strategies:    {list}                                        ║
║ Symbols:       {count}                                      ║
║ Status:        {Scanning / Waiting / Trading}              ║
╚══════════════════════════════════════════════════════════════╝

Commands:
- Press Ctrl+C to stop gracefully
- Run 'status' for current positions
```

## Error Handling

### Configuration Error
```
[ERROR] Configuration error: {message}
[ERROR] Fix: Edit config/trading_profile.yml
[ERROR] Example: cp config/trading_profile.example.yml config/trading_profile.yml
```

### Authentication Error
```
[ERROR] Not authenticated
[ERROR] Fix: Run 'python -m cli.main login'
```

### Market Closed
```
[WARNING] Market is closed
[INFO] Options:
1. Start in wait mode (will trade when market opens)
2. Exit and restart later
```

### Strategy Error
```
[ERROR] Failed to load strategy: {name}
[ERROR] {exception message}
[WARNING] Continuing with remaining strategies
```

## Startup Log

**Log entry format:**
```json
{
  "timestamp": "2026-01-15T09:15:00",
  "event": "BOT_START",
  "mode": "paper",
  "capital": 100000,
  "strategies": ["smc", "patterns"],
  "symbols": 50,
  "status": "success"
}
```

## CLI Usage

```bash
# Standard startup
python -m cli.main start-bot

# With specific config
python -m cli.main start-bot --config my_config.yml

# Force paper trading
python -m cli.main start-bot --paper

# Start in background (Linux/Mac)
nohup python -m cli.main start-bot > bot.log 2>&1 &
```
