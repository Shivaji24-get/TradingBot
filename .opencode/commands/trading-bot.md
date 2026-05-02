---
description: AI trading automation command center — show menu or analyze signal
---

Trading-bot router. Arguments provided: "$ARGUMENTS"

If arguments contain a trade signal or symbol (keywords like "BUY", "SELL", "signal", "NSE:", "BANKNIFTY", "price", "RSI"), the skill will execute auto-analysis mode.

Otherwise, the discovery menu will be shown.

Load the trading-bot skill:
```
skill({ name: "trading-bot" })
```
