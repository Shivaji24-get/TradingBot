# TradingBot Data Contract

This document defines which files belong to the **User Layer** (never auto-updated, contains personal data) and which belong to the **System Layer** (auto-updatable, contains code and templates).

## The Rule

**If a file is in the User Layer, no update process may read, modify, or delete it.**

**If a file is in the System Layer, it can be safely replaced with the latest version.**

---

## User Layer (NEVER Auto-Updated)

These files contain your personal trading configuration, history, and work product. Updates will NEVER modify them.

| File/Directory | Purpose |
|----------------|---------|
| `config/trading_profile.yml` | Your trading identity, preferences, and risk settings |
| `config/secrets.yml` | API keys and sensitive credentials (if separated) |
| `data/trades.md` | Complete trade history with P&L |
| `data/positions.md` | Active and closed positions log |
| `data/signals.md` | Signal history with performance tracking |
| `data/scan_history.tsv` | Market scan history and dedup records |
| `data/daily_pnl.md` | Daily P&L summaries |
| `logs/*.log` | Trading activity logs |
| `output/*.csv` | Exported trade reports |
| `output/*.json` | Exported metrics and analytics |
| `state/` | Runtime state persistence |
| `backups/` | Manual backups of configuration |

## System Layer (Safe to Auto-Update)

These files contain system logic, scripts, and templates that improve with each release.

| File/Directory | Purpose |
|----------------|---------|
| `ARCHITECTURE.md` | System architecture documentation |
| `DATA_CONTRACT.md` | This file - data separation rules |
| `core/*.py` | Core workflow modules (pipeline, tracker, metrics) |
| `strategies/*.py` | Trading strategy implementations |
| `api/*.py` | API client code |
| `utils/*.py` | Utility functions |
| `auth/*.py` | Authentication handling |
| `cli/*.py` | Command-line interface |
| `scripts/*.py` | Automation and utility scripts |
| `tests/*.py` | Test suite |
| `templates/*.html` | Report templates |
| `config/settings.yml` | Default system settings (not user profile) |
| `VERSION` | Current version number |

---

## File Formats

### YAML Configuration (trading_profile.yml)

```yaml
trader:
  name: "Your Name"
  email: "your@email.com"
  timezone: "Asia/Kolkata"

risk_profile:
  risk_per_trade: 0.02        # 2% per trade
  max_positions: 5            # Max concurrent positions
  max_daily_loss: 0.05        # 5% daily stop
  
trading_preferences:
  default_symbols:
    - "NSE:NIFTY50-INDEX"
    - "NSE:BANKNIFTY-INDEX"
  market_session:
    open: "09:15"
    close: "15:30"
```

### Markdown Tracking (trades.md)

```markdown
# Trade History

| # | Date | Symbol | Side | Entry | Exit | Qty | P&L | Status | Notes |
|---|------|--------|------|-------|------|-----|-----|--------|-------|
| 001 | 2026-05-02 | NSE:NIFTY50-INDEX | BUY | 22500 | 22650 | 50 | +7500 | Closed | Breakout pattern |
```

### TSV Format (scan_history.tsv)

Tab-separated values for machine parsing:
```
date	symbol	signal	score	price	volume	notes
2026-05-02	NSE:NIFTY50-INDEX	BUY	85	22500.50	150000	High volume breakout
```

---

## Migration Safety

When updating the TradingBot system:

1. **BACKUP FIRST**: Always backup your `config/` and `data/` directories
2. **VERIFY PRESENCE**: Ensure User Layer files exist after update
3. **CHECK INTEGRITY**: Run `python scripts/verify_pipeline.py` to validate

## Adding Custom Data

If you need to store additional personal data:

1. Create files in `data/` or `config/` directories
2. Follow existing naming conventions
3. Document the purpose in your own notes
4. Never store sensitive data in System Layer files

---

## Git Configuration

Add to `.gitignore`:
```
# User Layer - never commit
config/trading_profile.yml
config/secrets.yml
data/
logs/
output/
state/
token.*
*.key
*.enc

# Temporary files
tmp/
__pycache__/
*.pyc
```

---

**Last Updated**: 2026-05-02
**Version**: 1.0.0
