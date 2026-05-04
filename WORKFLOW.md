# TradingBot Workflow Documentation

> **End-to-end system flow, data architecture, and component interactions**

---

## 📋 Overview

This document provides a comprehensive view of how TradingBot operates, from market data ingestion to trade execution and performance tracking. It covers:

1. **System Architecture Flow** — High-level data movement
2. **Trading Pipeline** — Step-by-step trading workflow
3. **Component Interactions** — Module communication patterns
4. **Data Flow** — Input → Processing → Output
5. **Automation & Triggers** — Background processes and events

---

## 🏗️ System Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TRADINGBOT SYSTEM                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   INPUT      │────▶│  PROCESSING  │────▶│   OUTPUT     │────▶│   STORAGE    │
│   LAYER      │     │   LAYER      │     │   LAYER      │     │   LAYER      │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Fyers API    │     │ Strategies   │     │ CLI Output   │     │ data/        │
│ Market Data  │     │ Indicators   │     │ Orders       │     │ logs/        │
│ User Config  │     │ Risk Manager │     │ Reports      │     │ output/      │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

---

## 🔄 Trading Pipeline Workflow

### Complete Trade Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         TRADE LIFECYCLE (Single Trade)                       │
└──────────────────────────────────────────────────────────────────────────────┘

     ┌─────────┐
     │  START  │
     └────┬────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. MARKET SCAN  │───▶│ 2. SIGNAL GEN   │───▶│ 3. SCORING      │
│                 │    │                 │    │                 │
│ • Fetch candles │    │ • RSI calc      │    │ • RSI: 30%      │
│ • Apply SMA     │    │ • SMA trend     │    │ • Trend: 30%    │
│ • Detect vol    │    │ • Volume spike  │    │ • Volume: 20%   │
└─────────────────┘    │ • Pattern det   │    │ • Pattern: 20%  │
                       └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │ Score ≥ 50?     │
                                              └────────┬────────┘
                                                       │
                                    ┌──────────────────┴──────────────────┐
                                    │ NO                                │ YES
                                    ▼                                    ▼
                         ┌─────────────────┐                  ┌─────────────────┐
                         │ SKIP SIGNAL     │                  │ 4. RISK CHECK   │
                         │ Log in tracker  │                  │                 │
                         └─────────────────┘                  │ • Portfolio heat│
                                                               │ • Position size │
                                                               │ • Daily limits  │
                                                               │ • R:R ratio     │
                                                               └─────────────────┘
                                                                           │
                                                                           ▼
                                                                  ┌─────────────────┐
                                                                  │ Risk Pass?      │
                                                                  └────────┬────────┘
                                                                           │
                                                        ┌──────────────────┴──────────────────┐
                                                        │ NO                                │ YES
                                                        ▼                                    ▼
                                             ┌─────────────────┐                   ┌─────────────────┐
                                             │ LOG REJECTION   │                   │ 5. EXECUTION    │
                                             │ (risk reason)   │                   │                 │
                                             └─────────────────┘                   │ • Place order   │
                                                                                   │ • Set stop-loss │
                                                                                   │ • Track in pos  │
                                                                                   └─────────────────┘
                                                                                               │
                                                                                               ▼
                                                                                   ┌─────────────────┐
                                                                                   │ 6. MONITORING   │
                                                                                   │                 │
                                                                                   │ • Price updates │
                                                                                   │ • P&L tracking  │
                                                                                   │ • SL adjustment │
                                                                                   └─────────────────┘
                                                                                               │
                                                                                               ▼
                                                                                   ┌─────────────────┐
                                                                                   │ 7. EXIT         │
                                                                                   │                 │
                                                                                   │ • Target hit    │
                                                                                   │ • Stop triggered│
                                                                                   │ • Manual close  │
                                                                                   └─────────────────┘
                                                                                               │
                                                                                               ▼
                                                                                   ┌─────────────────┐
                                                                                   │ 8. RECORDING    │
                                                                                   │                 │
                                                                                   │ • Save to trades│
                                                                                   │ • Update metrics│
                                                                                   │ • Daily summary │
                                                                                   └─────────────────┘
                                                                                               │
                                                                                               ▼
                                                                                          ┌─────────┐
                                                                                          │   END   │
                                                                                          └─────────┘
```

---

## 📊 Data Flow Architecture

### Input → Processing → Output

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

LAYER 1: INPUT SOURCES
──────────────────────────────────────────────────────────────────────────────────

┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│ FYERS API          │  │ CONFIGURATION      │  │ USER INPUT       │
│                    │  │                    │  │                  │
│ • Historical data  │  │ • config.ini       │  │ • CLI commands   │
│ • Live quotes      │  │ • trading_profile  │  │ • Symbol lists   │
│ • Order responses  │  │ • strategy.json    │  │ • Parameters     │
└─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                                  ▼

LAYER 2: DATA INGESTION & NORMALIZATION
──────────────────────────────────────────────────────────────────────────────────

┌────────────────────────────────────────────────────────────────────┐
│ API CLIENT (api/)                                                    │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│ │ client.py   │──▶│ market_data │──▶│ orders.py   │──▶│ funds.py    │  │
│ │             │  │ .py         │  │             │  │             │  │
│ │ • Auth      │  │ • History   │  │ • Place     │  │ • Balance   │  │
│ │ • Rate limit│  │ • Quotes    │  │ • Modify    │  │ • Margins   │  │
└─────────────┬─┘  └─────────────┘  └─────────────┘  └─────────────┘  │
              │                                                        │
              ▼                                                        │
┌────────────────────────────────────────────────────────────────────┐
│ AUTH MODULE (auth/)                                                  │
│ ┌─────────────────┐                                                │
│ │ token_manager   │  • OAuth flow                                  │
│ │ .py             │  • Token encryption                            │
│ │                 │  • Auto-refresh                                │
└─────────────────┬─┘                                                │
                  │                                                    │
                  └────────────────────────────────────────────────────┘
                                    │
                                    ▼

LAYER 3: PROCESSING ENGINE
──────────────────────────────────────────────────────────────────────────────────

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STRATEGIES (strategies/)                                                         │
│                                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │ scanner.py   │──▶│ indicators   │──▶│ signal_scorer│──▶│ pattern_     │    │
│  │              │   │ .py          │   │ .py          │   │ detector.py  │    │
│  │ • Multi-stock│   │ • RSI/SMA    │   │ • Weights    │   │ • Flags      │    │
│  │ • Batch proc │   │ • Volume     │   │ • Score calc │   │ • Triangles  │    │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘    │
│         │                                                                  │    │
│         ▼                                                                  │    │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │ smart_money  │   │ risk_manager │   │ order_exec   │   │ live_engine  │    │
│  │ .py          │   │ .py          │   │ .py          │   │ .py          │    │
│  │ • HTF bias   │   │ • Position   │   │ • Auto-trade │   │ • Streaming  │    │
│  │ • SMC logic  │   │ • SL calc    │   │ • SL/TP      │   │ • Real-time  │    │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼

LAYER 4: CORE ORCHESTRATION
──────────────────────────────────────────────────────────────────────────────────

┌─────────────────────────────────────────────────────────────────────────────────┐
│ CORE MODULES (core/)                                                             │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │ pipeline.py                                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Signal Gen  │─▶│ Risk Check  │─▶│ Execution   │─▶│ Tracking    │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │ tracker.py   │   │ metrics.py   │   │ scheduler.py │   │ retry.py     │   │
│  │              │   │              │   │              │   │              │   │
│  │ • Trades     │   │ • Win rate   │   │ • Market open│   │ • Exponential│   │
│  │ • Positions  │   │ • Sharpe     │   │ • Intervals  │   │   backoff    │   │
│  │ • Signals    │   │ • Drawdown   │   │ • Reports    │   │ • Circuit    │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │   breaker    │   │
│                                                            └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼

LAYER 5: OUTPUT & STORAGE
──────────────────────────────────────────────────────────────────────────────────

┌─────────────────────────────────────────────────────────────────────────────────┐
│ CLI OUTPUT (cli/)                                                                │
│ ┌────────────────────────────────────────────────────────────────────────────┐  │
│ │ Rich tables, progress bars, color-coded signals, order confirmations        │  │
└────────────────────────────────────────────────────────────────────────────┬─┘  │
                                                                             │     │
┌────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│ DATA STORAGE (data/, logs/, output/)                                             │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │ trades.md    │  │ positions.md │  │ signals.md   │  │ scan_history │       │
│ │              │  │              │  │              │  │ .tsv         │       │
│ │ • Entry/exit │  │ • Open pos   │  │ • Score      │  │ • Timestamp  │       │
│ │ • P&L        │  │ • Unrealized │  │ • Outcome    │  │ • Symbols    │       │
│ │ • Strategy   │  │ • SL/TP      │  │ • Notes      │  │ • Results    │       │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                                              │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│ │ *.log (JSON) │  │ reports/     │  │ exports/     │                      │
│ │              │  │              │  │              │                      │
│ │ • Structured │  │ • Daily P&L  │  │ • CSV        │                      │
│ │ • Debug info │  │ • Performance│  │ • JSON       │                      │
└──────────────┘  └──────────────┘  └──────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Key Components & Responsibilities

### 1. API Layer (`api/`)

| Component | Responsibility | Key Functions |
|-----------|---------------|---------------|
| `client.py` | Fyers API authentication & session management | `authenticate()`, `get_client()`, token refresh |
| `market_data.py` | Historical and real-time market data | `get_historical_data()`, `get_quotes()` |
| `orders.py` | Order lifecycle management | `place_order()`, `modify_order()`, `cancel_order()` |
| `funds.py` | Account balance and margin info | `get_funds()`, `get_margins()` |
| `holdings.py` | Current portfolio positions | `get_holdings()` |

### 2. Strategy Layer (`strategies/`)

| Component | Responsibility | Key Functions |
|-----------|---------------|---------------|
| `scanner.py` | Multi-symbol analysis orchestration | `scan_all()`, `scan_symbol()`, batch processing |
| `indicators.py` | Technical calculations | `calculate_all_indicators()`, RSI, SMA, Volume |
| `signal_scorer.py` | Probability scoring algorithm | `score_signal()`, weighted component calculation |
| `pattern_detector.py` | Chart pattern recognition | `detect_all()`, flag/triangle/pennant detection |
| `smart_money.py` | SMC bias analysis | HTF trend confirmation, institutional order flow |
| `risk_manager.py` | Pre-trade risk validation | `validate_position()`, heat calculation, SL calc |
| `order_executor.py` | Automated order placement | `execute_signal()`, SL/TP attachment |
| `live_engine.py` | Real-time streaming loop | `start()`, polling loop, auto-trading trigger |

### 3. Core Layer (`core/`)

| Component | Responsibility | Key Functions |
|-----------|---------------|---------------|
| `pipeline.py` | End-to-end workflow orchestration | `run_scan()`, `execute_trade()`, health checks |
| `tracker.py` | Trade/position/signal persistence | `add_trade()`, `add_position()`, `get_trades()` |
| `metrics.py` | Performance analytics | Win rate, Sharpe ratio, drawdown calculations |
| `scheduler.py` | Background job management | Market open detection, periodic scans |
| `retry.py` | Resilient API communication | Exponential backoff, circuit breaker pattern |

### 4. CLI Layer (`cli/`)

| Component | Responsibility | Key Functions |
|-----------|---------------|---------------|
| `main.py` | CLI entry point & command routing | Typer app initialization, command registration |
| `commands.py` | All CLI command implementations | `scan_cmd()`, `analyze_cmd()`, `place_order_cmd()` |

### 5. Utility Layer (`utils/`)

| Component | Responsibility | Key Functions |
|-----------|---------------|---------------|
| `config.py` | Configuration loading & validation | `load_config()`, profile management |
| `logger.py` | Structured logging setup | JSON formatting, log rotation |
| `helpers.py` | Common utilities | Market hours check, data formatting |
| `exporter.py` | Data export functionality | CSV, JSON export for external analysis |

---

## ⚡ Automation & Triggers

### Scheduled Operations

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         AUTOMATION SCHEDULE                                  │
└──────────────────────────────────────────────────────────────────────────────┘

MARKET OPEN (9:15 AM IST)
├── Load trading profile
├── Authenticate with Fyers
├── Initialize tracker with yesterday's data
├── Run pre-market scan (optional)
└── Start live engine (if configured)

DURING MARKET HOURS (9:15 AM - 3:30 PM IST)
├── Live scan loop (configurable interval: 5s-300s)
│   ├── Fetch latest quotes
│   ├── Generate signals
│   ├── Evaluate scores
│   ├── Risk check
│   └── Auto-trade (if enabled)
├── Position monitoring (P&L updates)
├── SL adjustment tracking
└── API health monitoring

MARKET CLOSE (3:30 PM IST)
├── Close all pending orders
├── Final position snapshot
├── Generate daily report
├── Export trade history
└── Cleanup temporary files

DAILY (End of Day)
├── Calculate daily metrics
├── Update performance charts
├── Archive old logs
└── Backup trade data

WEEKLY (Saturday)
├── Generate weekly report
├── Performance analysis
├── Strategy effectiveness review
└── Data cleanup (optional)
```

### Event-Driven Triggers

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         EVENT TRIGGERS                                       │
└──────────────────────────────────────────────────────────────────────────────┘

SIGNAL EVENT
    Condition: Score ≥ threshold
    Action:    Risk validation → Order placement (if auto-trade enabled)
    Handler:   order_executor.py → risk_manager.py

RISK BREACH EVENT
    Condition: Portfolio heat > 6% OR Daily loss > 3%
    Action:    Alert user + Block new trades
    Handler:   risk_manager.py → cli output

POSITION EXIT EVENT
    Condition: SL hit OR Target hit OR Manual close
    Action:    Record trade → Update metrics → Log to trades.md
    Handler:   tracker.py → metrics.py

API ERROR EVENT
    Condition: Rate limit OR Connection failure OR Auth expiry
    Action:    Retry with backoff → Circuit breaker (if persistent)
    Handler:   retry.py → scheduler.py (pause/resume)

MARKET STATUS EVENT
    Condition: Market open/close
    Action:    Start/stop live engine
    Handler:   scheduler.py → live_engine.py
```

---

## 🔄 Component Communication Patterns

### Request-Response Flow

```
CLI Command → commands.py → strategies/ → api/ → Fyers API
     ↑                                             │
     └─────────────── Response ←───────────────────┘
```

### Event-Driven Flow

```
Live Engine (Publisher)
    ↓
Signal Generated Event
    ↓
Risk Manager (Subscriber) → Validates → Pass/Fail
    ↓
Order Executor (Subscriber) → Places order (if pass)
    ↓
Tracker (Subscriber) → Records position
```

### Pipeline Orchestration Flow

```
pipeline.py (Orchestrator)
    ├── Calls scanner.py → Returns signals
    ├── Calls risk_manager.py → Validates
    ├── Calls order_executor.py → Executes (if validated)
    └── Calls tracker.py → Records outcome
```

---

## 📦 Data Contracts

### User Layer (Gitignored, Never Auto-Updated)

| File | Format | Content | Access Pattern |
|------|--------|---------|----------------|
| `config/trading_profile.yml` | YAML | User preferences, risk settings | Read on startup |
| `data/trades.md` | Markdown | Complete trade history | Append on exit |
| `data/positions.md` | Markdown | Position lifecycle | Update on events |
| `data/signals.md` | Markdown | Signal history with outcomes | Append on generation |
| `logs/*.log` | JSON Lines | Structured logs | Continuous append |
| `output/*` | Various | Reports, exports | Write on demand |

### System Layer (Auto-Updatable)

| File | Format | Content | Update Frequency |
|------|--------|---------|------------------|
| `core/*.py` | Python | Core modules | Version releases |
| `strategies/*.py` | Python | Strategy logic | Version releases |
| `cli/*.py` | Python | CLI commands | Version releases |
| `modes/*.md` | Markdown | Gemini context | As needed |
| `.gemini/commands/*.toml` | TOML | AI command defs | As needed |

---

## 🔍 Error Handling & Recovery

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      ERROR HANDLING HIERARCHY                                │
└──────────────────────────────────────────────────────────────────────────────┘

Level 1: TRANSIENT ERRORS (Auto-retry)
├── API rate limit (429)
├── Network timeout
└── Temporary unavailability
    Action: Exponential backoff retry (3 attempts)

Level 2: RECOVERABLE ERRORS (Graceful degradation)
├── Invalid symbol format
├── Data fetch failure (single symbol)
└── Partial scan failure
    Action: Log warning, continue with available data

Level 3: CRITICAL ERRORS (Stop & Alert)
├── Authentication failure
├── Persistent API errors (>5 failures)
├── Risk limit breach
└── Circuit breaker triggered
    Action: Halt operations, alert user, preserve state

Level 4: FATAL ERRORS (Emergency shutdown)
├── Corrupted data files
├── Disk space full
└── Unhandled exceptions
    Action: Emergency shutdown, preserve logs
```

---

## 🚀 Performance Considerations

### Optimization Strategies

| Area | Strategy | Implementation |
|------|----------|----------------|
| **API Calls** | Batch requests | `scan_all()` fetches multiple symbols efficiently |
| **Data Storage** | Markdown over DB | Human-readable, version-controlled |
| **Signal Calculation** | Vectorized pandas | NumPy operations over loops |
| **Live Streaming** | Configurable intervals | 5s-300s based on strategy |
| **Token Storage** | Encryption at rest | `token.enc` with Fernet encryption |
| **Memory** | Streaming processing | Process symbols in batches |

---

## 🎯 Quick Reference

### Entry Points

| Use Case | Entry Point | Key File |
|----------|-------------|----------|
| Manual scan | `python -m cli.main scan` | `cli/commands.py:scan_cmd()` |
| Start bot | `python -m cli.main start-bot` | `cli/commands.py:start_bot_cmd()` |
| Live trading | `--live` flag | `strategies/live_engine.py` |
| AI analysis | `gemini /trading-bot-analyze` | `modes/analyze.md` |
| Daily report | Automated | `scripts/daily_report.py` |

### Key Data Structures

```python
# Signal Result (strategies/scanner.py)
{
    "symbol": "NSE:RELIANCE-EQ",
    "price": 1430.80,
    "signal": "SELL",
    "score": 73,
    "rsi": 69.05,
    "sma_20": 1354.26,
    "pattern": "flag",
    "pattern_confidence": 0.78
}

# Trade Record (core/tracker.py)
TradeRecord(
    id="T001",
    symbol="NSE:RELIANCE-EQ",
    side="SELL",
    entry_price=1430.80,
    exit_price=1410.00,
    qty=10,
    pnl=208.00,
    status="WIN"
)
```

---

**For detailed architecture, see [ARCHITECTURE.md](ARCHITECTURE.md)**  
**For data management rules, see [DATA_CONTRACT.md](DATA_CONTRACT.md)**  
**For Gemini CLI integration, see [GEMINI.md](GEMINI.md)**

---

*Last Updated: 2025*  
*TradingBot v2.0 — Career-Ops Inspired Architecture*
