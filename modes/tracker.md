# Mode: tracker — Trading Activity Overview

Display comprehensive overview of trading activity and performance.

## Tracker Data Sources

**Primary files:**
- `data/trades.md` — Complete trade history
- `data/positions.md` — Open and closed positions
- `data/signals.md` — Signal history
- `data/scan-history.tsv` — Market scan history

## Display Options

### Option 1: Dashboard View

**Summary Cards:**
```
┌─────────────────────────────────────────────────────────────┐
│ TODAY'S SUMMARY                                             │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│ Trades: 3   │ P&L: +₹2,450 │ Win Rate:  │ Open Pos: 2     │
│             │ (+2.45%)    │ 67%         │ Risk: ₹3,200    │
└─────────────┴─────────────┴─────────────┴─────────────────┘
```

### Option 2: Period Selection

**Available periods:**
- Today
- This Week
- This Month
- Last 30 Days
- Last 90 Days
- Year to Date
- All Time
- Custom Range

### Option 3: Performance Metrics

**Key Metrics Display:**

| Category | Metric | Value |
|----------|--------|-------|
| Returns | Total P&L | ₹{X} ({X}%) |
| | Avg Daily Return | {X}% |
| | Best Day | ₹{X} |
| | Worst Day | ₹{X} |
| Trades | Total | {X} |
| | Wins | {X} ({X}%) |
| | Losses | {X} ({X}%) |
| | Win Streak | {X} |
| | Loss Streak | {X} |
| Risk | Max Drawdown | {X}% |
| | Current DD | {X}% |
| | Avg Risk/Trade | {X}% |
| | Portfolio Heat | {X}% |

### Option 4: Trade History

**Recent Trades Table:**
```markdown
| # | Date | Symbol | Side | Entry | Exit | Qty | P&L | Result |
|---|------|--------|------|-------|------|-----|-----|--------|
```

### Option 5: Position Status

**Open Positions:**
```markdown
| Symbol | Side | Entry | Current | Stop | Target | P&L | R:R | Age |
|--------|------|-------|---------|------|--------|-----|-----|-----|
```

**Closed Positions (today):**
```markdown
| Symbol | Side | Entry | Exit | Qty | Gross P&L | Net P&L | R Multiple |
|--------|------|-------|------|-----|-----------|---------|------------|
```

### Option 6: Signal Analysis

**Signal Performance:**
```markdown
| Signal Score | Trades | Win Rate | Avg P&L | Expectancy |
|--------------|--------|----------|---------|------------|
| ≥ 80 (Strong)| {X}    | {X}%     | ₹{X}    | ₹{X}       |
| 60-79 (Good) | {X}    | {X}%     | ₹{X}    | ₹{X}       |
| < 60 (Weak)  | {X}    | {X}%     | ₹{X}    | ₹{X}       |
```

### Option 7: Strategy Performance

**By Strategy:**
```markdown
| Strategy | Trades | Win Rate | P&L | Avg R | Profit Factor |
|----------|--------|----------|-----|-------|---------------|
| SMC      | {X}    | {X}%     | ₹{X}| {X}   | {X}           |
| Patterns | {X}    | {X}%     | ₹{X}| {X}   | {X}           |
| Mean Rev | {X}    | {X}%     | ₹{X}| {X}   | {X}           |
```

## Tracker Commands

| Command | Description |
|---------|-------------|
| `tracker` | Show today's summary |
| `tracker --week` | This week |
| `tracker --month` | This month |
| `tracker --all` | All time |
| `tracker --symbol RELIANCE` | Filter by symbol |
| `tracker --strategy SMC` | Filter by strategy |

## Report Generation

**Generate detailed report:**

```bash
python scripts/daily_report.py --date 2026-01-15
```

Output: `reports/daily-{YYYY-MM-DD}.md`

## Data Integrity

**Health checks:**
- Verify sequential trade numbering
- Check for orphaned positions
- Validate P&L calculations
- Ensure all signals have reports

**Run verification:**
```bash
python scripts/verify_pipeline.py
```
