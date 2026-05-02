# TradingBot — AI-Powered Trading Automation (Gemini CLI)

> This file is auto-loaded by the Gemini CLI as persistent context.
> It is the Gemini equivalent of CLAUDE.md for the TradingBot project.
> All slash commands are defined in `.gemini/commands/`.

## What is TradingBot

AI-powered trading automation for Indian stock markets (NSE): automated signal generation, risk management, backtesting, paper trading, and live execution with Fyers API.

## Data Contract (CRITICAL)

**User Layer (NEVER auto-updated — your personalizations live here):**
- `config/trading_profile.yml`, `modes/_profile.md`
- `data/*`, `logs/*`, `output/*`, `reports/*`

**System Layer (auto-updatable — do NOT put user data here):**
- `modes/_shared.md`, `modes/*.md` (except _profile.md)
- `GEMINI.md`, `core/*.py`, `strategies/*.py`, `scripts/*.py`
- `templates/*`, `cli/*.py`

**THE RULE:** When the user asks to customize anything (risk parameters, strategy settings, symbols, notification preferences), ALWAYS write to `modes/_profile.md` or `config/trading_profile.yml`. NEVER edit `modes/_shared.md` for user-specific content.

## Update Check

On the first message of each session, run the update checker silently:

```bash
python scripts/health_check.py
```

Parse output:
- `{"status": "healthy"}` → proceed
- `{"status": "warning"}` → show warnings
- `{"status": "error"}` → stop and report issues

## Gemini CLI Commands

When using [Gemini CLI](https://github.com/google-gemini/gemini-cli), the following slash commands are available (defined in `.gemini/commands/`):

| Command | Description |
|---------|-------------|
| `/trading-bot` | Show menu or analyze signal with args |
| `/trading-bot-start` | Start the trading bot |
| `/trading-bot-stop` | Stop the trading bot gracefully |
| `/trading-bot-status` | Check bot status and positions |
| `/trading-bot-scan` | Scan market for opportunities |
| `/trading-bot-analyze` | Deep AI analysis of symbol |
| `/trading-bot-backtest` | Run strategy backtest |
| `/trading-bot-evaluate` | Evaluate signal with A-F scoring |
| `/trading-bot-compare` | Compare multiple setups |
| `/trading-bot-risk` | Risk assessment |
| `/trading-bot-tracker` | Trading activity overview |
| `/trading-bot-strategy` | Strategy management |
| `/trading-bot-paper` | Paper trading mode |
| `/trading-bot-metrics` | Performance analytics |
| `/trading-bot-notify` | Configure alerts |

**All commands share the same evaluation logic** in `modes/*.md`. The `modes/` files are shared between Claude Code, OpenCode, and Gemini CLI.

## First Run — Onboarding (IMPORTANT)

**Before doing ANYTHING else, check if the system is set up.** Run these checks silently:

1. Does `config/trading_profile.yml` exist (not just .example)?
2. Does `modes/_profile.md` exist (not just .template)?
3. Do `data/` files exist (trades.md, positions.md, signals.md)?

If `modes/_profile.md` is missing, copy from `modes/_profile.template.md` silently.

**If ANY of these is missing, enter onboarding mode.** Do NOT proceed with trading commands until basics are in place.

### Step 1: Trading Profile (required)

If `config/trading_profile.yml` is missing:
> "I don't have your trading profile yet. Let's set it up:
> 
> 1. What's your name?
> 2. What's your experience level? (Beginner/Intermediate/Advanced)
> 3. What's your risk tolerance? (Conservative/Moderate/Aggressive)
> 4. Initial capital to trade? (for paper trading)
> 5. Which markets? (NSE Cash/Futures/Options)
> 
> This helps me personalize the trading recommendations."

Copy from `config/trading_profile.example.yml` and fill in their answers.

### Step 2: User Profile (required)

If `modes/_profile.md` is missing, copy from template and ask:
> "Let's set up your personal trading preferences:
> 
> - What's your primary trading strategy? (SMC/Patterns/Trend/Mix)
> - Preferred symbols to trade?
> - Risk per trade (default 1%)?
> - Any symbols or setups to avoid?
> 
> Store these in modes/_profile.md for personalization."

### Step 3: Data Files (auto-create)

If data files missing, create them:
```markdown
# data/trades.md
| # | Date | Symbol | Side | Entry | Exit | Qty | P&L | Strategy | Status |
|---|------|--------|------|-------|------|-----|-----|----------|--------|

# data/positions.md
| Symbol | Side | Entry | Stop | Target | Qty | Status | Opened | Strategy |
|--------|------|-------|------|--------|-----|--------|--------|----------|

# data/signals.md
| # | Date | Symbol | Signal | Score | Status | P&L | Report |
|---|------|--------|--------|-------|--------|-----|--------|
```

### Step 4: Authentication Check

Check Fyers authentication:
> "To trade, you'll need to authenticate with Fyers. 
> Run: python -m cli.main login
> 
> Or if you prefer paper trading first (recommended for beginners), we can skip this for now."

### Step 5: Ready

Once all files exist:
> "You're all set! You can now:
> - Run `/trading-bot scan` to find opportunities
> - Run `/trading-bot` and paste a symbol for analysis
> - Start paper trading with `/trading-bot-paper`
> 
> All settings are customizable — just ask me to change anything.
> 
> **Recommended:** Start with paper trading for at least 20 trades before going live."

## Skill Modes

| If the user... | Mode to load |
|----------------|--------------|
| Pastes a symbol or signal | auto-analyze (evaluate + report + tracker) |
| Asks to evaluate trade | evaluate |
| Wants to compare setups | compare |
| Asks for market analysis | analyze |
| Wants backtest | backtest |
| Checks positions/status | status / tracker |
| Wants risk assessment | risk |
| Needs strategy help | strategy |
| Sets up notifications | notify |
| Paper trading | paper |
| Views performance | metrics |

## Core Trading Concepts

### Signal Scoring (A-F)

Every trade signal is evaluated on:
- **A: Signal Quality** — Technical indicators, patterns (25 pts)
- **B: Risk Assessment** — Stop-loss, R:R ratio (25 pts)
- **C: Timing Analysis** — Market condition, entry timing (15 pts)
- **D: Setup Validation** — HTF alignment, liquidity (20 pts)
- **E: Execution Plan** — Entry, exit, management (15 pts)
- **F: AI Validation** — Gemini confidence score (15 pts)

**Global Score 0-100:**
- 85+ → STRONG (Execute)
- 70-84 → GOOD (Execute)
- 50-69 → MODERATE (Paper/Reduced)
- < 50 → WEAK (Skip)

### Risk Management (Hard Rules)

1. **Stop Loss Required** — Every position
2. **Risk Per Trade** — Max 2% of capital (default 1%)
3. **Portfolio Heat** — Max 6% total at risk
4. **Position Size** — Max 20% of portfolio per trade
5. **Daily Loss Limit** — Stop trading at 3% loss

### SMC (Smart Money Concepts)

Key concepts for institutional-level analysis:
- **FVG** — Fair Value Gap (imbalance zones)
- **OB** — Order Block (institutional order zones)
- **Liquidity** — Sweeps of retail stop-losses
- **MSS** — Market Structure Shift (trend change)
- **HTF** — Higher Timeframe bias

## Main Files

| File | Function |
|------|----------|
| `data/trades.md` | Trade history tracker |
| `data/positions.md` | Active positions |
| `data/signals.md` | Signal history |
| `config/trading_profile.yml` | Trading configuration |
| `modes/_profile.md` | Personal preferences |
| `core/gemini_advisor.py` | AI signal analysis |
| `core/tracker.py` | Activity tracking |
| `strategies/scanner.py` | Market scanning |
| `reports/` | Analysis reports |

## Ethical Use — CRITICAL

- **NEVER trade without user confirmation** — AI suggests, user decides
- **Discourage overtrading** — If score < 50, explicitly recommend against
- **Quality over quantity** — One A-grade trade beats five C-grade trades
- **Risk first, reward second** — Always show potential loss before gain
- **Paper trading recommended** — Especially for new strategies
- **Never guarantee profits** — Present probability, not certainty

## Safety Protocols

1. **Always verify market open** before trading
2. **Check authentication** before live orders
3. **Confirm risk limits** before execution
4. **Log every action** for accountability
5. **Circuit breaker** on consecutive losses

## CI/CD and Quality

- **Health checks:** `scripts/health_check.py`
- **Pipeline verification:** `scripts/verify_pipeline.py`
- **Daily reports:** `scripts/daily_report.py`

## Stack and Conventions

- Python 3.9+, YAML configuration, Markdown data
- Fyers API for Indian markets
- Gemini API for AI analysis (optional)
- Telegram/email notifications (optional)
- Reports in `reports/`, data in `data/`

## Personalization

This system is designed to be customized. When the user asks you to change:
- Risk parameters → edit `config/trading_profile.yml`
- Strategy preferences → edit `modes/_profile.md`
- Notification settings → edit `config/trading_profile.yml`
- Default symbols → edit `config/trading_profile.yml`

**Common customization requests:**
- "Change risk per trade to 2%" → edit trading_profile.yml
- "Add these symbols to my scan list" → edit trading_profile.yml
- "I prefer SMC only, disable patterns" → edit trading_profile.yml strategies section
- "Update my Telegram chat ID" → edit trading_profile.yml

---

**Note:** This is a financial trading system. Always prioritize risk management and user safety over performance optimization.
