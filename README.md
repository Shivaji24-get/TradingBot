# 🤖 TradingBot — AI-Powered Algorithmic Trading for Indian Markets

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Fyers API](https://img.shields.io/badge/Fyers-API%20v3-green.svg)](https://myapi.fyers.in/)

> **Automated signal generation, risk management, and optional order execution
> for NSE/BSE markets via the Fyers API.**

---

## ⚡ Quick Start (5 minutes)

```bash
# 1 — Clone
git clone https://github.com/Shivaji24-get/TradingBot.git
cd TradingBot

# 2 — Virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3 — Install dependencies
pip install -r requirements.txt

# 4 — Set API credentials (NEVER commit these)
export FYERS_CLIENT_ID="your_client_id"      # from https://myapi.fyers.in/
export FYERS_SECRET_KEY="your_secret_key"

# 5 — Create your config
cp config/trading_profile.example.yml config/trading_profile.yml
# Edit the file to add your symbol list and risk settings

# 6 — Initialise data files
python scripts/init_tracking.py

# 7 — Authenticate with Fyers
python -m cli.main login

# 8 — Verify everything is ready
python scripts/health_check.py

# 9 — Start paper trading (safe, no real money)
python -m cli.main start-bot --paper
```

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [CLI Commands](#cli-commands)
- [Workflow](#workflow)
- [Risk Management](#risk-management)
- [Scoring System](#scoring-system)
- [Troubleshooting](#troubleshooting)
- [Security](#security)

---

## Architecture

```
TradingBot/
├── api/              Fyers API wrappers (data, orders, funds)
├── auth/             OAuth2 token management (encrypted storage)
├── cli/              Typer-based CLI (20+ commands)
├── core/
│   ├── pipeline.py   Orchestrates the per-symbol trading cycle
│   ├── tracker.py    Appends trades/signals to data/*.md files
│   ├── metrics.py    Calculates Sharpe, drawdown, win rate
│   ├── scheduler.py  Market-hours-aware job runner
│   └── state_machine.py  IDLE → SCANNING → ORDER_PENDING → …
├── strategies/
│   ├── scanner.py        Multi-symbol scanning (historical + SMC)
│   ├── smart_money.py    3-tier SMC: HTF bias → MTF setup → LTF entry
│   ├── signal_scorer.py  RSI(30%) + Trend(30%) + Volume(20%) + Pattern(20%)
│   ├── fvg_detector.py   Fair Value Gaps
│   ├── order_block.py    Institutional order zones
│   ├── mss_detector.py   Market Structure Shifts / CHoCH
│   ├── liquidity.py      PDH/PDL sweep detection
│   └── live_smc_engine.py  Real-time scanning with auto-trade
├── utils/            Config loading, logging, scheduling helpers
├── scripts/          health_check, init_tracking, daily_report
└── config/
    ├── trading_profile.example.yml   ← committed (template)
    └── trading_profile.yml           ← NOT committed (your secrets)
```

---

## Features

| Category | Capability |
|----------|-----------|
| **Scanning** | Single symbol, custom list, or full index (NIFTY50, BANKNIFTY) |
| **Strategies** | RSI+SMA momentum, Smart Money Concepts (HTF→MTF→LTF), chart patterns |
| **SMC** | FVG, Order Blocks, Liquidity sweeps, MSS/CHoCH, Harmonic patterns |
| **Scoring** | 0–100 probability score with component breakdown |
| **Risk** | Position sizing, stop-loss, daily loss limit, max positions |
| **Modes** | Paper (safe default), Live (explicit opt-in) |
| **Tracking** | trades.md, positions.md, signals.md (append-only) |
| **Reporting** | Daily P&L, win rate, Sharpe ratio, max drawdown |
| **AI** | Optional Google Gemini signal explanation & validation |
| **Alerts** | Telegram and email notifications |

---

## Installation

### Prerequisites

- Python 3.9+
- Fyers trading account with API access ([create app](https://myapi.fyers.in/))
- Chrome browser (for Selenium-based OAuth login)

### Production install

```bash
pip install -r requirements.txt
```

### Development install (includes Selenium, test tools, AI)

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

---

## Configuration

All settings live in `config/trading_profile.yml` (gitignored).
Copy the template and edit:

```bash
cp config/trading_profile.example.yml config/trading_profile.yml
```

### Key sections

```yaml
risk_profile:
  risk_per_trade: 0.01        # 1% of capital per trade (start here)
  max_positions: 5
  max_daily_loss: 0.03        # Stop trading at 3% daily loss
  default_stop_loss_pct: 1.5

trading_preferences:
  default_symbols:
    - "NSE:NIFTY50-INDEX"
    - "NSE:RELIANCE-EQ"
  auto_trading:
    enabled: false            # KEEP FALSE until weeks of paper trading done
    paper_trading: true

api:
  fyers:
    client_id: "${FYERS_CLIENT_ID}"   # Set as env var
    secret_key: "${FYERS_SECRET_KEY}" # Set as env var
```

---

## CLI Commands

```bash
# Authentication
python -m cli.main login                          # Fyers OAuth

# Market scanning
python -m cli.main scan --index NIFTY50           # Scan NIFTY50 stocks
python -m cli.main scan --symbol NSE:RELIANCE-EQ  # Single symbol
python -m cli.main scan --index BANKNIFTY --smc   # SMC 3-tier scan
python -m cli.main scan --symbol NSE:SBIN-EQ --live --interval 10  # Live

# Analysis
python -m cli.main analyze --symbol NSE:TCS-EQ
python -m cli.main evaluate --symbol NSE:HDFCBANK-EQ
python -m cli.main compare --symbols "NSE:RELIANCE-EQ,NSE:TCS-EQ,NSE:INFY-EQ"

# Bot management
python -m cli.main start-bot --paper              # Safe paper trading
python -m cli.main start-bot --live               # Real money (caution!)
python -m cli.main status --detailed
python -m cli.main positions

# Performance
python -m cli.main metrics --category all --period 30d
python -m cli.main tracker --period week
python -m cli.main report --format markdown

# Account
python -m cli.main get-funds
python -m cli.main get-holdings
```

---

## Workflow

```
Every {scan_interval} seconds (default: 60 s):

  is_market_open()? ──NO──► sleep ──► repeat
        │
       YES
        │
  For each symbol:
    1. get_historical_data()   [1H trend candles]
    2. get_historical_data()   [5M entry candles]   ← dual TF
    3. generate_signal()       [RSI + SMA + volume + patterns]
    4. SMC analysis            [HTF bias → MTF setup → LTF entry]
    5. risk_check()            [score ≥ 75, heat ≤ 6%, limits OK]
    6. paper/live order        [simulated or real]
    7. tracker.add_signal()    [append → data/signals.md]
```

---

## Risk Management

| Parameter | Default | Description |
|-----------|---------|-------------|
| `risk_per_trade` | 1% | Max capital loss per trade |
| `max_positions` | 5 | Concurrent positions |
| `max_daily_loss` | 3% | Daily stop-trading threshold |
| `default_stop_loss_pct` | 1.5% | Default SL distance |
| `default_take_profit_pct` | 4.5% | Default TP distance |
| `min_risk_reward_ratio` | 2.0 | Minimum R:R to take trade |

---

## Scoring System

Each signal receives a weighted score (0–100):

| Component | Weight | Condition |
|-----------|--------|-----------|
| RSI | 30 pts | < 30 (BUY) or > 70 (SELL) = full score |
| Trend (SMA) | 30 pts | SMA20 > SMA50 = bullish trend |
| Volume | 20 pts | Current > 1.5× average |
| Pattern | 20 pts | Flag/triangle/pennant detected |

**Score thresholds:**

| Range | Grade | Action |
|-------|-------|--------|
| 85–100 | Strong | Execute at full size |
| 70–84 | Good | Execute at standard size |
| 50–69 | Moderate | Paper trade or reduce size |
| 0–49 | Weak | Skip |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `AttributeError: 'SMCResult' has no attribute 'mtf_aligned'` | Old smart_money.py | Apply fix from ANALYSIS_REPORT.md |
| `TypeError: 'tzinfo' is not callable` | `tz` variable shadowing | Apply scheduler.py fix |
| `KeyError: 'mtf_aligned'` in display | Missing key in scanner result | Apply scanner.py fix |
| `Not logged in` | Token expired | `python -m cli.main login` |
| `Credentials missing or placeholder` | Env vars not set | `export FYERS_CLIENT_ID=...` |
| `Algo orders not allowed (code -50)` | Standard app ID | Contact Fyers for algo-enabled app |
| `No signals for hours` | Market sideways or threshold too high | Lower `confidence_threshold` in YAML |

---

## Security

See [SECURITY.md](SECURITY.md) for:
- Credential rotation steps (required if you cloned the original repo)
- Environment variable setup
- Secure local-only config file usage
- What is and is NOT committed to Git

**TL;DR:** Never commit `config/trading_profile.yml`, `token.key`, or `token.enc`.
Always set credentials via env vars: `FYERS_CLIENT_ID` and `FYERS_SECRET_KEY`.

---

## Disclaimer

This software is for **educational and research purposes only**.
- Trading involves substantial risk of loss
- Past performance does not guarantee future results
- Always test with **paper trading** before using real money
- This bot does **not** provide financial advice
- You are **solely responsible** for your trading decisions

---

## License

MIT — see [LICENSE](LICENSE)
