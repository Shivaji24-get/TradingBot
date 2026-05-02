# Mode: stop — Trading Bot Shutdown

Execute graceful trading bot shutdown.

## Shutdown Triggers

### User-Initiated
- Ctrl+C pressed
- `stop-bot` command executed
- Stop signal received

### Automatic Triggers
- Daily loss limit reached
- Critical error encountered
- Market closed and configured to stop
- Scheduled stop time reached

## Shutdown Sequence

### Phase 1: Stop Signal Processing (0-2 seconds)

```
[SHUTDOWN] Stop signal received
[SHUTDOWN] Reason: {user_request / loss_limit / error / market_closed}
[SHUTDOWN] Current time: {HH:MM:SS}
```

### Phase 2: Pause New Signals (2-3 seconds)

```
[INFO] Stopping signal generation...
[INFO] No new positions will be opened
[INFO] Pending orders: {count} - will be cancelled
```

**Actions:**
- Set `accepting_new_signals = False`
- Cancel all pending entry orders
- Stop scanner/scheduler

### Phase 3: Position Handling (3-10 seconds)

**User Configuration:**
```yaml
shutdown:
  position_handling: "hold"  # Options: hold, close, notify
  close_method: "market"     # Options: market, limit
  time_limit: 300           # Seconds to wait for closes
```

**Option A: Hold Positions (default)**
```
[INFO] Hold mode selected
[INFO] {X} open positions will remain active
[INFO] Stop-loss orders remain in place
[INFO] Position monitoring continues
```

**Option B: Close All Positions**
```
[INFO] Close mode selected
[INFO] Closing {X} positions...
[POSITION] Closing {Symbol} {Side}... ✓
[POSITION] Closing {Symbol} {Side}... ✓
...
[INFO] All positions closed
[INFO] Final P&L: ₹{X}
```

**Option C: Notify Only**
```
[INFO] Notify mode selected
[INFO] {X} open positions require manual management
[INFO] Telegram/email alert sent
[INFO] Position details logged to output/shutdown-{time}.txt
```

### Phase 4: Data Persistence (10-15 seconds)

```
[INFO] Saving trading state...
[INFO] Syncing positions to data/positions.md... ✓
[INFO] Syncing trades to data/trades.md... ✓
[INFO] Syncing signals to data/signals.md... ✓
[INFO] State saved successfully
```

**Save:**
- Current positions with updated P&L
- Any closed trades from this session
- Signal history
- Scanner cache
- Configuration state

### Phase 5: Report Generation (15-20 seconds)

```
[INFO] Generating session summary...
[INFO] Report saved to: reports/session-{YYYYMMDD-HHMM}.md
```

**Session Report:**
```markdown
# Trading Session Report

**Session Start:** {datetime}
**Session End:** {datetime}
**Duration:** {X} hours {X} minutes
**Mode:** {Paper/Live}

## Summary
| Metric | Value |
|--------|-------|
| Total Trades | {X} |
| Open Positions (end) | {X} |
| Closed Positions | {X} |
| Gross P&L | ₹{X} |
| Net P&L (after costs) | ₹{X} |
| Win Rate | {X}% |
| Best Trade | ₹{X} |
| Worst Trade | ₹{X} |

## Open Positions at Shutdown

| Symbol | Side | Entry | Current | Stop | Target | P&L |
|--------|------|-------|---------|------|--------|-----|
| ... | ... | ... | ... | ... | ... | ... |

## Closed Trades This Session

| Symbol | Side | Entry | Exit | P&L | R Multiple |
|--------|------|-------|------|-----|------------|
| ... | ... | ... | ... | ... | ... |

## Signals Generated

| Time | Symbol | Signal | Score | Executed |
|------|--------|--------|-------|----------|
| ... | ... | ... | ... | ... |

## System Events

- {time}: Bot started
- {time}: First trade executed
- {time}: Position {symbol} closed +₹{X}
- {time}: Shutdown initiated

## Performance Metrics

- Sharpe Ratio: {X}
- Profit Factor: {X}
- Average R: {X}
- Max Drawdown: {X}%
```

### Phase 6: Notification (20-25 seconds)

**If notifications enabled:**
```
[INFO] Sending shutdown notification...
[INFO] Telegram alert: ✓
[INFO] Email alert: ✓
```

**Notification content:**
```
🛑 Trading Bot Stopped

Session Summary:
• Duration: {X}h {X}m
• Trades: {X}
• P&L: ₹{X} ({X}%)
• Open Positions: {X}

Status: {Graceful / Positions Held / All Closed}

Next Steps: {based on position handling mode}
```

### Phase 7: Cleanup (25-30 seconds)

```
[INFO] Cleaning up resources...
[INFO] Closing API connections... ✓
[INFO] Flushing logs... ✓
[INFO] Releasing locks... ✓
[INFO] Shutdown complete
```

## Emergency Shutdown

**If critical error or force stop:**

```
[EMERGENCY] Immediate shutdown initiated
[EMERGENCY] Reason: {critical_error_description}
[EMERGENCY] Saving emergency state...
[EMERGENCY] State saved to: output/emergency-{timestamp}.json
[EMERGENCY] Please review positions manually
[EMERGENCY] Shutdown complete
```

**Emergency state file includes:**
- All open positions
- Pending orders
- Last known P&L
- Error details
- Recovery instructions

## Post-Shutdown State

### Positions Held
- User must manually monitor
- Stop-loss orders remain active
- Notifications continue (if enabled)
- Can restart bot to resume management

### Positions Closed
- All trades completed
- Final P&L realized
- Capital released
- Clean state for next session

## CLI Usage

```bash
# Standard shutdown (graceful)
python -m cli.main stop-bot

# With position handling override
python -m cli.main stop-bot --close-all
python -m cli.main stop-bot --hold-all

# Emergency stop
python -m cli.main stop-bot --force

# Scheduled stop (for cron)
python -m cli.main stop-bot --at 15:25
```

## Restart Procedure

**After shutdown:**

1. Review session report
2. Check open positions (if any)
3. Analyze performance
4. Adjust strategy if needed
5. Restart when ready:
   ```bash
   python -m cli.main start-bot
   ```

## Safety Checks

**Before confirming shutdown:**

```
⚠️  SHUTDOWN CONFIRMATION

You are about to stop the trading bot.

Current Status:
• Open Positions: {X}
• Pending Orders: {X}
• Unrealized P&L: ₹{X}

Position Handling: {hold/close/notify}

Are you sure? [y/N]: 
```

**Override with --force:**
```bash
python -m cli.main stop-bot --force
```
