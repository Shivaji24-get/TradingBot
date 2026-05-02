# Mode: notify — Notification Configuration

Configure and manage trade alerts and notifications.

## Notification Channels

### Telegram

**Setup Process:**
1. Create bot with @BotFather
2. Get bot token
3. Get chat ID
4. Test connection
5. Enable alerts

**Configuration:**
```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    chat_id: "123456789"
    events:
      - signal_generated    # New signal found
      - trade_executed      # Order filled
      - position_exited     # Trade closed with P&L
      - stop_triggered      # Stop loss hit
      - target_hit          # Profit target reached
      - high_risk_signal    # Signal with unusual risk
      - error               # System errors
      - daily_summary       # EOD report
      - bot_started         # Bot startup
      - bot_stopped         # Bot shutdown
```

**Message Format:**
```
🔔 TRADING ALERT

📈 Signal Generated
Symbol: NSE:RELIANCE-EQ
Signal: BUY
Score: 82/100
Price: ₹2,452

📊 Setup:
Entry: ₹2,450
Stop: ₹2,420 (1.2%)
Target: ₹2,550 (R:3.3)

⚡ Quick Actions:
[Execute Paper] [Execute Live] [Analyze]
```

### Email

**Setup Process:**
1. Configure SMTP settings
2. Set from/to addresses
3. Test email delivery
4. Select events

**Configuration:**
```yaml
notifications:
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "your_email@gmail.com"
    password: "${EMAIL_PASSWORD}"  # Use env variable
    from_address: "trading_bot@yourdomain.com"
    to_address: "your_email@gmail.com"
    events:
      - trade_executed
      - position_exited
      - daily_summary
      - error
    include_attachments: true  # Attach reports
```

**Email Template:**
```html
<h2>Trading Bot - Daily Summary</h2>
<p>Date: 2026-01-15</p>

<table>
  <tr><td>Trades:</td><td>5</td></tr>
  <tr><td>P&L:</td><td>+₹3,450</td></tr>
  <tr><td>Win Rate:</td><td>60%</td></tr>
</table>

<p>See attached report for details.</p>
```

### Webhook

**For integration with external systems:**
```yaml
notifications:
  webhook:
    enabled: true
    url: "https://your-app.com/webhook/trading-bot"
    headers:
      Authorization: "Bearer ${WEBHOOK_TOKEN}"
    events:
      - all  # Or specific events
    retry: 3
    timeout: 10
```

**Payload Format:**
```json
{
  "event": "trade_executed",
  "timestamp": "2026-01-15T10:30:00Z",
  "data": {
    "symbol": "NSE:RELIANCE-EQ",
    "side": "BUY",
    "price": 2452,
    "quantity": 40,
    "order_id": "E26011500001"
  }
}
```

## Alert Types

### Signal Alerts

**Trigger:** Score ≥ threshold (default 75)

**Telegram:**
```
🎯 HIGH QUALITY SIGNAL

NSE:TCS-EQ | Score: 84/100

📈 BUY Setup
Entry: ₹3,850
Stop: ₹3,800 (1.3%)
Target: ₹4,000 (R:3.0)

HTF: ✅ Bullish
Sweep: ✅ Completed
MSS: ✅ Confirmed
FVG: ✅ Present

[View Chart] [Execute Paper] [Execute Live]
```

### Trade Execution Alerts

**Entry:**
```
✅ TRADE EXECUTED

Symbol: NSE:SBIN-EQ
Side: BUY
Qty: 100
Fill Price: ₹650.50

Risk: ₹2,000 (2%)
Position: 10% of portfolio
```

**Exit:**
```
📊 POSITION CLOSED

Symbol: NSE:SBIN-EQ
Side: SELL (exit)
Qty: 100
Fill Price: ₹675.00

💰 P&L: +₹2,450 (+3.77%)
R-Multiple: +1.2R

Time in Trade: 2h 34m
```

### Risk Alerts

**Portfolio Heat Warning:**
```
⚠️ RISK ALERT

Portfolio Heat: 5.2% / 6% limit
Approaching maximum risk exposure!

Consider:
- Reducing position sizes
- Closing weak positions
- Waiting for exits before new entries
```

**Daily Loss Limit:**
```
🛑 DAILY LOSS LIMIT REACHED

Current Daily P&L: -₹3,050 (-3.05%)
Limit: 3%

Bot has PAUSED new entries.
Review and manual override to continue.
```

### Daily Summary

**EOD Report:**
```
📈 DAILY TRADING SUMMARY
2026-01-15

Performance:
├── Trades: 8
├── Win Rate: 62% (5W / 3L)
├── Gross P&L: +₹4,500
├── Commissions: -₹160
└── Net P&L: +₹4,340 (+4.34%)

Open Positions: 3
Portfolio Heat: 4.2%

Best Trade: NSE:RELIANCE +₹1,800
Worst Trade: NSE:ICICIBANK -₹650

Full report: reports/daily-2026-01-15.md
```

## Notification Testing

**Test command:**
```bash
# Test all channels
python -m cli.main notify --test

# Test specific channel
python -m cli.main notify --test --channel telegram
python -m cli.main notify --test --channel email

# Send test alert
python -m cli.main notify --test-alert
```

## Rate Limiting

**Prevent spam:**
```yaml
notifications:
  rate_limiting:
    max_per_minute: 10
    max_per_hour: 50
    cooldown_period: 60  # seconds between similar alerts
    
  grouping:
    enabled: true
    window: 300  # Group alerts within 5 minutes
    max_group_size: 5
```

**Grouped Notification Example:**
```
📦 BATCH ALERT (5 signals in last 5 min)

Top Signals:
1. RELIANCE | BUY | 85/100
2. TCS | BUY | 82/100
3. SBIN | SELL | 78/100
4. HDFCBANK | BUY | 76/100
5. ICICIBANK | SELL | 74/100

[View All] [Execute Best] [Dismiss]
```

## Quiet Hours

**Disable non-critical alerts:**
```yaml
notifications:
  quiet_hours:
    enabled: true
    start: "22:00"
    end: "08:00"
    timezone: "Asia/Kolkata"
    allow_critical: true  # Still send errors, stops
```

## CLI Commands

```bash
# Configure notifications
python -m cli.main notify --setup

# Enable/disable channels
python -m cli.main notify --enable telegram
python -m cli.main notify --disable email

# Add/remove events
python -m cli.main notify --add-event trade_executed --channel telegram
python -m cli.main notify --remove-event signal_generated --channel telegram

# View configuration
python -m cli.main notify --config

# Test notifications
python -m cli.main notify --test
```

## Security

**Best Practices:**
1. Store tokens/passwords in environment variables
2. Use bot tokens (not personal tokens) for Telegram
3. Enable 2FA on email accounts
4. Use app-specific passwords for email
5. Rotate tokens periodically
6. Never commit credentials to git

**Example .env file:**
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
EMAIL_PASSWORD=your_app_specific_password
WEBHOOK_TOKEN=secret_token_here
```

## Troubleshooting

**Telegram not working:**
- Check bot token format
- Verify chat ID (try @userinfobot)
- Ensure bot is added to chat
- Check bot hasn't been blocked

**Email not sending:**
- Verify SMTP settings
- Check for 2FA requirements
- Use app-specific password
- Check spam folders
- Verify firewall isn't blocking port

**Duplicate alerts:**
- Check cooldown_period setting
- Verify alert logic isn't duplicated
- Look for multiple notification handlers
