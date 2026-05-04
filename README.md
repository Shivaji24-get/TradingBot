# 🤖 TradingBot — AI-Powered Algorithmic Trading System

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Fyers API](https://img.shields.io/badge/Fyers-API-green.svg)](https://myapi.fyers.in/)
[![Gemini CLI](https://img.shields.io/badge/Gemini-CLI-purple.svg)](https://github.com/aquilax/gemini-cli)

> **Professional-grade algorithmic trading bot for Indian stock markets**  
> Built for the Fyers API with real-time scanning, AI analysis, risk management, and automated execution.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [CLI Commands](#cli-commands)
- [Scoring System](#scoring-system)
- [Risk Management](#risk-management)
- [Gemini CLI Integration](#gemini-cli-integration)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## 🎯 Overview

TradingBot is a comprehensive algorithmic trading system designed for Indian equity markets. It combines technical analysis, pattern recognition, and risk management to generate actionable trading signals with probability-based confidence scores.

### What Makes It Different

| Feature | TradingBot | Typical Bots |
|---------|-----------|--------------|
| **Signal Quality** | Multi-factor scoring (RSI, Trend, Volume, Pattern) | Single indicator |
| **Risk Control** | Position sizing, stop-loss, daily limits | Basic order placement |
| **Live Trading** | Real-time streaming with auto-execution | Batch-only |
| **AI Integration** | Gemini CLI commands for analysis | None |
| **Tracking** | Complete trade/position/signal history | No persistence |
| **Modes** | Paper trading, backtesting, live | Live only |

---

## ✨ Key Features

### Market Analysis
- **Multi-Stock Scanning** — Scan single symbols, custom lists, or entire indices (NIFTY50, BANKNIFTY, FINNIFTY)
- **Technical Indicators** — RSI, SMA (20/50), Volume Analysis
- **Pattern Detection** — Flags, Triangles, Pennants with confidence scoring
- **Smart Money Concepts** — SMC-based bias detection on higher timeframes

### Signal Generation
- **Probability Scoring** — Weighted algorithm (RSI 30%, Trend 30%, Volume 20%, Pattern 20%)
- **A-F Evaluation** — Comprehensive signal quality assessment
- **Multi-Timeframe Analysis** — LTF (5m) + HTF (15m) confirmation
- **Confidence Thresholds** — Auto-trading eligible at ≥75%

### Execution & Risk
- **Live Streaming** — Real-time data with configurable polling (5s-300s)
- **Auto-Trading** — Optional automatic order placement for high-confidence signals
- **Position Sizing** — Percentage-based allocation (default: 10% per trade)
- **Stop-Loss** — Automatic SL calculation (default: 2% from entry)
- **Daily Limits** — Max 5 trades/day, 3 concurrent positions

### Tracking & Analytics
- **Trade History** — Complete P&L tracking with markdown exports
- **Position Monitor** — Real-time unrealized P&L updates
- **Signal Archive** — Historical signal performance analysis
- **Daily Reports** — Automated P&L summaries

### AI Integration
- **Gemini CLI Commands** — Natural language trading analysis
- **AI Signal Explanation** — Understand why signals fire
- **Strategy Suggestions** — AI-powered trading recommendations

---

## 🛠️ Tech Stack

### Core Technologies
| Component | Technology | Purpose |
|-----------|------------|---------|
| **Language** | Python 3.9+ | Core runtime |
| **CLI Framework** | Typer | Command-line interface |
| **Data Analysis** | Pandas, NumPy | Technical calculations |
| **HTTP Client** | Requests | API communication |
| **Encryption** | Cryptography | Secure token storage |
| **Formatting** | Rich | Terminal output |

### Trading & Market Data
| Component | Technology | Purpose |
|-----------|------------|---------|
| **Broker API** | Fyers API v3 | Order execution & market data |
| **Data Format** | Pandas DataFrame | Time-series analysis |
| **Indicators** | TA-Lib patterns | Chart pattern detection |

### AI & Automation
| Component | Technology | Purpose |
|-----------|------------|---------|
| **AI Commands** | Gemini CLI | Natural language trading |
| **Task Runner** | Custom scheduler | Background jobs |
| **Health Checks** | Python scripts | System verification |

### Configuration & Storage
| Component | Technology | Purpose |
|-----------|------------|---------|
| **Config Format** | YAML + INI | Profile & system settings |
| **Data Storage** | Markdown + TSV | Human-readable tracking |
| **Logging** | Structured JSON | Machine-parseable logs |

---

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- Fyers trading account with API access
- Windows/Linux/macOS

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone https://github.com/Shivaji24-get/TradingBot.git
cd TradingBot

# 2. Create virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python -m cli.main --help
```

---

## ⚙️ Configuration

### 1. Fyers API Credentials

Create `config.ini` in the project root:

```ini
[DEFAULT]
client_id = YOUR_FYERS_CLIENT_ID
secret_key = YOUR_FYERS_SECRET_KEY
redirect_uri = http://127.0.0.1:5000/fyers/callback
```

**Get your credentials:**
1. Login to [Fyers API Dashboard](https://myapi.fyers.in/)
2. Create an app with "Trading" permission
3. Copy Client ID and Secret Key

### 2. Trading Profile (Optional)

Create `config/trading_profile.yml` for personalized settings:

```yaml
trader_identity:
  name: "Your Name"
  style: "swing"  # scalper, daytrader, swing, position
  experience: "intermediate"  # novice, intermediate, advanced

risk_profile:
  max_portfolio_heat: 6.0  # % of capital at risk
  max_position_size: 20.0  # % per position
  max_daily_loss: 3.0      # % of capital
  max_concurrent_positions: 3
  min_risk_reward_ratio: 1.5

trading_preferences:
  default_symbols:
    - "NSE:RELIANCE-EQ"
    - "NSE:TCS-EQ"
    - "NSE:HDFCBANK-EQ"
  default_timeframe: "D"
  auto_trading: false
  confirmation_required: true
```

### 3. Authenticate

```bash
python -m cli.main login
```

This opens a browser for Fyers OAuth. Copy the auth code from the redirect URL.

---

## 📖 Usage

### Basic Scanning

```bash
# Scan a single stock
python -m cli.main scan --symbol NSE:RELIANCE-EQ

# Scan multiple stocks
python -m cli.main scan --symbols "NSE:RELIANCE-EQ,NSE:TCS-EQ,NSE:INFY-EQ"

# Scan an index (top 10 by score)
python -m cli.main scan --index NIFTY50 --top 10

# Custom timeframe and candle limit
python -m cli.main scan --index BANKNIFTY --timeframe D --limit 100
```

### Live Trading Mode

```bash
# Live scan with 5-second intervals
python -m cli.main scan --symbol NSE:SBIN-EQ --live --interval 5

# Live scan with auto-trading (≥75% confidence)
python -m cli.main scan --symbol NSE:RELIANCE-EQ --live --auto-trade --threshold 75

# Monitor multiple symbols
python -m cli.main scan --symbols "NSE:SBIN-EQ,NSE:ICICIBANK-EQ" --live --interval 10
```

### AI-Powered Analysis

```bash
# Deep analysis with pattern detection
python -m cli.main analyze --symbol NSE:RELIANCE-EQ

# Evaluate signal quality (A-F scoring)
python -m cli.main evaluate --symbol NSE:INFY-EQ

# Compare multiple setups
python -m cli.main compare --symbols "RELIANCE,TCS,SBIN"
```

### Bot Management

```bash
# Start trading bot (paper mode)
python -m cli.main start-bot --paper

# Start trading bot (live mode)
python -m cli.main start-bot --live

# Check bot status
python -m cli.main status --detailed

# View risk metrics
python -m cli.main risk --portfolio

# View trading history
python -m cli.main tracker --period today
```

### Order Management

```bash
# Place market order
python -m cli.main place-order --symbol NSE:RELIANCE-EQ --side BUY --qty 10

# Place limit order
python -m cli.main place-order --symbol NSE:SBIN-EQ --side SELL --qty 5 --type LIMIT --price 1080.50

# Check order status
python -m cli.main order-status --order-id 230415000000001

# View portfolio
python -m cli.main get-holdings
python -m cli.main get-funds
```

---

## 📁 Project Structure

```
TradingBot/
├── 📁 api/                      # API clients and endpoints
│   ├── __init__.py
│   ├── client.py             # Fyers API client wrapper
│   ├── market_data.py        # Historical/quotes data
│   ├── orders.py             # Order placement/management
│   ├── funds.py              # Account balance
│   ├── holdings.py           # Portfolio positions
│   └── profile.py            # User profile data
│
├── 📁 auth/                     # Authentication
│   ├── __init__.py
│   └── token_manager.py      # OAuth token encryption/storage
│
├── 📁 cli/                      # Command-line interface
│   ├── __init__.py
│   ├── main.py               # CLI entry point (Typer)
│   └── commands.py           # All CLI command implementations
│
├── 📁 core/                     # Core workflow modules
│   ├── __init__.py
│   ├── pipeline.py           # Trading workflow orchestration
│   ├── tracker.py            # Trade/position/signal tracking
│   ├── metrics.py            # Performance analytics
│   ├── scheduler.py          # Job scheduling
│   ├── retry.py              # API retry mechanisms
│   ├── state_machine.py      # Trading state management
│   └── gemini_advisor.py     # AI integration layer
│
├── 📁 strategies/               # Trading strategies
│   ├── __init__.py
│   ├── scanner.py            # Multi-stock scanner
│   ├── signal_scorer.py      # Probability scoring
│   ├── pattern_detector.py   # Chart pattern detection
│   ├── indicators.py         # Technical indicators
│   ├── smart_money.py        # SMC strategy
│   ├── order_executor.py     # Auto-trading execution
│   ├── live_engine.py        # Real-time streaming
│   ├── risk_manager.py       # Risk controls
│   └── parser.py             # Strategy config parser
│
├── 📁 utils/                    # Utilities
│   ├── __init__.py
│   ├── config.py             # Configuration loaders
│   ├── logger.py             # Structured logging
│   ├── helpers.py            # Helper functions
│   └── exporter.py           # Data export (CSV/JSON)
│
├── 📁 config/                   # Configuration files
│   └── trading_profile.yml   # User trading profile
│
├── 📁 data/                     # User data (gitignored)
│   ├── trades.md             # Trade history
│   ├── positions.md          # Position log
│   └── signals.md            # Signal history
│
├── 📁 modes/                    # Gemini CLI modes
│   ├── _shared.md            # Shared context
│   ├── scan.md               # Scanning mode
│   ├── analyze.md            # Analysis mode
│   ├── evaluate.md           # Signal evaluation
│   ├── risk.md               # Risk assessment
│   ├── start.md              # Bot startup
│   └── ...                   # Additional modes
│
├── 📁 .gemini/                  # Gemini CLI commands
│   └── commands/             # TOML command definitions
│
├── 📁 .opencode/                # OpenCode commands
│   └── commands/             # MD command definitions
│
├── 📁 scripts/                  # Automation scripts
│   ├── health_check.py       # System verification
│   ├── daily_report.py       # Daily P&L reports
│   └── verify_pipeline.py    # Pipeline integrity
│
├── 📁 tests/                    # Test suite
├── 📁 logs/                     # Log files (gitignored)
├── 📁 output/                   # Generated reports (gitignored)
│
├── 📄 config.ini                # API credentials (gitignored)
├── 📄 strategy.json             # Strategy configuration
├── 📄 requirements.txt          # Python dependencies
├── 📄 ARCHITECTURE.md           # System architecture
├── 📄 DATA_CONTRACT.md          # Data management rules
├── 📄 GEMINI.md                 # Gemini CLI context
├── 📄 WORKFLOW.md               # End-to-end workflow (see below)
└── 📄 README.md                 # This file
```

---

## 🖥️ CLI Commands Reference

### Core Trading Commands

| Command | Description | Example |
|---------|-------------|---------|
| `scan` | Scan stocks for trading signals | `python -m cli.main scan --index NIFTY50` |
| `analyze` | Deep technical analysis of a symbol | `python -m cli.main analyze --symbol NSE:RELIANCE-EQ` |
| `evaluate` | Evaluate signal quality (A-F scoring) | `python -m cli.main evaluate --symbol NSE:INFY-EQ` |
| `compare` | Compare multiple trade setups | `python -m cli.main compare --symbols "RELIANCE,TCS"` |

### Bot Management Commands

| Command | Description | Example |
|---------|-------------|---------|
| `start-bot` | Start the trading bot | `python -m cli.main start-bot --paper` |
| `stop-bot` | Stop the trading bot | `python -m cli.main stop-bot` |
| `status` | Check bot status & positions | `python -m cli.main status --detailed` |
| `risk` | Risk assessment | `python -m cli.main risk --portfolio` |
| `tracker` | View trading activity | `python -m cli.main tracker --period today` |

### Order Commands

| Command | Description | Example |
|---------|-------------|---------|
| `place-order` | Place a trade | `python -m cli.main place-order --symbol SYM --side BUY --qty 10` |
| `order-status` | Check order status | `python -m cli.main order-status --order-id ID` |
| `get-holdings` | View portfolio | `python -m cli.main get-holdings` |
| `get-funds` | Check balance | `python -m cli.main get-funds` |

### Scan Options

| Option | Description | Default |
|--------|-------------|---------|
| `--symbol` | Single symbol | - |
| `--symbols` | Comma-separated list | - |
| `--index` | Index group | - |
| `--timeframe` | Candle timeframe | `D` |
| `--limit` | Number of candles | 100 |
| `--top` | Show top N results | 5 |
| `--live` | Enable live mode | False |
| `--interval` | Polling interval (seconds) | 5 |
| `--auto-trade` | Auto-place orders | False |
| `--threshold` | Minimum score for trading | 75 |

---

## 🎯 Scoring System

### Probability Calculation

| Component | Weight | Calculation |
|-----------|--------|-------------|
| **RSI** | 30% | Distance from oversold/overbought thresholds |
| **Trend** | 30% | SMA alignment (bullish/bearish) |
| **Volume** | 20% | Volume spike vs average |
| **Pattern** | 20% | Pattern confidence score |

### Score Thresholds

| Score | Level | Action |
|-------|-------|--------|
| ≥75% | 🟢 High Confidence | Auto-trading eligible |
| 50-74% | 🟡 Medium Confidence | Manual review recommended |
| <50% | 🔴 Low Confidence | Skip or paper trade |

---

## 🛡️ Risk Management

### Built-in Protections

| Control | Default | Description |
|---------|---------|-------------|
| **Position Size** | 10% per trade | Max capital allocation per position |
| **Stop Loss** | 2% from entry | Automatic SL calculation |
| **Daily Loss** | 3% of capital | Stop trading if exceeded |
| **Max Trades** | 5 per day | Daily trade limit |
| **Max Positions** | 3 concurrent | Position count limit |
| **Portfolio Heat** | 6% max | Total unrealized risk |

### Pre-Trade Checks

Every trade validates:
- ✅ Signal score ≥ threshold
- ✅ Risk:Reward ≥ minimum (1.5:1)
- ✅ Daily loss limit not exceeded
- ✅ Max positions not reached
- ✅ Market is open

---

## 🤖 Gemini CLI Integration

TradingBot includes natural language AI commands through Gemini CLI:

```bash
# Analyze a trading setup
gemini /trading-bot-analyze "RELIANCE showing flag pattern at 1430"

# Scan for opportunities
gemini /trading-bot-scan "Find bullish setups in NIFTY50"

# Evaluate signal quality
gemini /trading-bot-evaluate "INFY BUY at 1181 with RSI 27"

# Check bot status
gemini /trading-bot-status

# Risk assessment
gemini /trading-bot-risk "Portfolio heat check"

# Full bot control
gemini /trading-bot-start --paper
gemini /trading-bot-stop
```

**Setup required:** Install [Gemini CLI](https://github.com/aquilax/gemini-cli) and navigate to the TradingBot directory.

---

## 🤝 Contributing

Contributions are welcome! Follow these steps:

```bash
# 1. Fork the repository

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and commit
git commit -m "feat: Add your feature description"

# 4. Push and create PR
git push origin feature/your-feature-name
```

### Commit Message Format

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `refactor:` — Code restructuring
- `test:` — Test additions

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) file.

---

## ⚠️ Disclaimer

**IMPORTANT: Trading involves substantial risk of loss.**

- This software is for **educational and research purposes only**
- **Past performance does not guarantee future results**
- Always test with **paper trading** before using real money
- Signals are algorithmic and **do not guarantee profits**
- You are **solely responsible** for your trading decisions
- This bot **does not provide financial advice**

By using this software, you acknowledge these risks and agree to use it at your own risk.

---

## 📚 Additional Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture & design
- [DATA_CONTRACT.md](DATA_CONTRACT.md) — Data management rules
- [WORKFLOW.md](WORKFLOW.md) — End-to-end workflow
- [GEMINI.md](GEMINI.md) — Gemini CLI integration

---

## 🙏 Acknowledgments

- [Fyers API](https://myapi.fyers.in/) — Market data & trading infrastructure
- [Rich](https://rich.readthedocs.io/) — Terminal formatting
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Gemini CLI](https://github.com/aquilax/gemini-cli) — AI integration

---

**Happy Trading! 📈 Trade Smart, Trade Safe.**
