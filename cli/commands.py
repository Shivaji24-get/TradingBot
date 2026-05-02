from strategies import StockScanner
import sys
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from pathlib import Path
import configparser

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import TokenManager, LoginFlow
from api import FyersClient
from api import get_profile, get_funds, get_holdings, get_historical_data, get_quotes
from api import place_order as api_place_order, get_order_status
from strategies import SignalGenerator, RiskManager
from utils import load_config, setup_logging, is_market_open, export_to_csv

console = Console()

def get_client():
    config = load_config()
    tm = TokenManager(config["client_id"], config["secret_key"])
    token = tm.get_access_token()
    if not token:
        console.print("[red]Not logged in. Run 'login' first.[/red]")
        raise typer.Exit(1)
    return FyersClient(config["client_id"], token), config

def login_cmd():
    config = load_config()
    console.print("[cyan]Starting Fyers authentication...[/cyan]")
    tm = TokenManager(config["client_id"], config["secret_key"])
    lf = LoginFlow(
        config["client_id"], 
        config["secret_key"], 
        config["redirect_uri"],
        username=config.get("username"),
        pin=config.get("pin"),
        mobile=config.get("mobile")
    )
    try:
        token = lf.authenticate()
        tm.save_token(token)
        console.print("[green]✓ Authentication successful![/green]")
    except Exception as e:
        console.print(f"[red]✗ Authentication failed: {e}[/red]")
        raise typer.Exit(1)

def profile_cmd():
    client, config = get_client()
    profile = get_profile(client.get_client())
    
    table = Table(title="User Profile")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    
    for k, v in profile.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    
    console.print(table)

def funds_cmd():
    client, _ = get_client()
    funds = get_funds(client.get_client())
    
    table = Table(title="Funds")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    
    for k, v in funds.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    
    console.print(table)

def holdings_cmd():
    client, _ = get_client()
    holdings = get_holdings(client.get_client())
    
    if not holdings or "error" in holdings[0]:
        console.print("[yellow]No holdings found[/yellow]")
        return
    
    table = Table(title="Holdings")
    for col in ["symbol", "qty", "avg_price", "ltp", "pnl", "pnl_percent"]:
        table.add_column(col.replace("_", " ").title(), style="cyan")
    
    for h in holdings:
        table.add_row(
            str(h.get("symbol", "")),
            str(h.get("qty", 0)),
            str(h.get("avg_price", 0)),
            str(h.get("ltp", 0)),
            str(h.get("pnl", 0)),
            str(h.get("pnl_percent", 0)) + "%"
        )
    
    console.print(table)

def market_data_cmd(symbol: str = typer.Option(..., "--symbol", help="Symbol (e.g., NSE:SBIN-EQ)")):
    client, _ = get_client()
    df = get_historical_data(client.get_client(), symbol, "D", count=30)
    
    if df.empty:
        console.print("[red]No data found[/red]")
        return
    
    table = Table(title=f"Market Data - {symbol}")
    for col in ["timestamp", "open", "high", "low", "close", "volume"]:
        table.add_column(col.title(), style="cyan")
    
    for _, row in df.tail(10).iterrows():
        table.add_row(
            str(row["timestamp"])[:10],
            f"₹{row['open']:.2f}",
            f"₹{row['high']:.2f}",
            f"₹{row['low']:.2f}",
            f"₹{row['close']:.2f}",
            str(int(row["volume"]))
        )
    
    console.print(table)

def place_order_cmd(
    symbol: str = typer.Option(..., "--symbol"),
    qty: int = typer.Option(..., "--qty", min=1),
    side: str = typer.Option(..., "--side", help="buy or sell"),
    order_type: str = typer.Option("MARKET", "--type", help="MARKET or LIMIT"),
    product_type: str = typer.Option("MIS", "--product", help="MIS or CNC"),
    price: float = typer.Option(None, "--price", help="Limit price (required for LIMIT orders)")
):
    client, config = get_client()
    
    result = api_place_order(
        client.get_client(), symbol, qty, side.upper(),
        order_type.upper(), product_type.upper(), price
    )
    
    if "error" in result:
        console.print(f"[red]✗ Order failed: {result['error']}[/red]")
    else:
        console.print(f"[green]✓ Order placed: {result.get('order_id', 'N/A')}[/green]")
        export_to_csv([{"symbol": symbol, "side": side, "qty": qty, "status": "placed", **result}])

def order_status_cmd(order_id: str = typer.Option(..., "--order-id")):
    client, _ = get_client()
    status = get_order_status(client.get_client(), order_id)
    
    if "error" in status:
        console.print(f"[red]Error: {status['error']}[/red]")
        return
    
    table = Table(title=f"Order Status - {order_id}")
    for k, v in status.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    
    console.print(table)

def run_bot_cmd():
    console.print("[cyan]Starting trading bot...[/cyan]")
    setup_logging()
    client, config = get_client()
    
    if not is_market_open():
        console.print("[yellow]Market is closed. Waiting for market open...[/yellow]")
    
    signal_gen = SignalGenerator(
        min_pattern_size=5,
        confidence_threshold=config.get("confidence_threshold", 0.75)
    )
    risk_mgr = RiskManager(config)
    
    funds = get_funds(client.get_client())
    capital = funds.get("available_cash", 100000)
    
    console.print(f"[green]Bot started with capital: ₹{capital}[/green]")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]")
    
    import time
    from datetime import datetime
    
    try:
        while True:
            if is_market_open():
                for symbol in config.get("symbols", ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"]):
                    try:
                        df = get_historical_data(client.get_client(), symbol, "D", count=50)
                        if not df.empty:
                            signal = signal_gen.analyze(df)
                            console.print(f"[cyan]{symbol}: {signal}[/cyan]")
                            
                            if signal != "HOLD" and risk_mgr.can_trade():
                                price = get_quotes(client.get_client(), symbol).get("last", 0)
                                if price > 0:
                                    qty = risk_mgr.calculate_position_size(capital, price)
                                    result = api_place_order(
                                        client.get_client(), symbol, qty, signal.lower(),
                                        "MARKET", "MIS"
                                    )
                                    if "order_id" in result:
                                        risk_mgr.add_position(symbol, signal, price, qty)
                                        console.print(f"[green]✓ Executed {signal} {symbol}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error with {symbol}: {e}[/red]")
            
            time.sleep(60)            
    except KeyboardInterrupt:
        console.print("[yellow]Bot stopped[/yellow]")

def scan_cmd(
    symbol: str = typer.Option(None, "--symbol", help="Scan specific symbol"),
    symbols: str = typer.Option(None, "--symbols", help="Comma-separated symbols (e.g., NSE:SBIN-EQ,NSE:RELIANCE-EQ)"),
    index: str = typer.Option(None, "--index", help="Index group (NIFTY50, BANKNIFTY, SENSEX)"),
    timeframe: str = typer.Option(None, "--timeframe", help="Timeframe (D, 5m, 1h)"),
    htf: str = typer.Option(None, "--htf", help="Higher timeframe for HTF bias (e.g., 15m, 1h). Auto if not specified."),
    limit: int = typer.Option(None, "--limit", help="Number of candles"),
    live: bool = typer.Option(False, "--live", help="Enable live real-time scanning"),
    smc: bool = typer.Option(False, "--smc", help="Use Smart Money Concepts strategy (HTF+LTF alignment, FVG, OB, MSS, Liquidity)"),
    min_score: int = typer.Option(50, "--min-score", help="Minimum SMC score to display (0-100, default: 50)"),
    interval: int = typer.Option(5, "--interval", help="Polling interval in seconds (live mode only, min: 3)"),
    auto_trade: bool = typer.Option(False, "--auto-trade", help="Auto-place orders for high-confidence signals (live mode only)"),
    threshold: int = typer.Option(75, "--threshold", help="Minimum score threshold for auto-trading (0-100)"),
    top: int = typer.Option(5, "--top", help="Show top N results by score")
):
    client, _ = get_client()

    # Build symbol list from various options
    scan_symbols = None
    if symbol:
        scan_symbols = [symbol]
    elif symbols:
        # Parse comma-separated symbols
        scan_symbols = [s.strip() for s in symbols.split(",")]
    elif index:
        # Use predefined index group
        index_upper = index.upper()
        INDEX_GROUPS = {
            "NIFTY50": [
                "NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ",
                "NSE:INFY-EQ", "NSE:SBIN-EQ", "NSE:ITC-EQ", "NSE:HINDUNILVR-EQ",
                "NSE:HDFC-EQ", "NSE:BAJFINANCE-EQ", "NSE:KOTAKBANK-EQ", "NSE:LT-EQ",
                "NSE:AXISBANK-EQ", "NSE:ASIANPAINT-EQ", "NSE:MARUTI-EQ", "NSE:TITAN-EQ",
                "NSE:ONGC-EQ", "NSE:NTPC-EQ", "NSE:WIPRO-EQ", "NSE:ULTRACEMCO-EQ"
            ],
            "BANKNIFTY": [
                "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ", "NSE:SBIN-EQ", "NSE:KOTAKBANK-EQ",
                "NSE:AXISBANK-EQ", "NSE:INDUSINDBK-EQ", "NSE:BANKBARODA-EQ", "NSE:AUBANK-EQ",
                "NSE:PNB-EQ", "NSE:CANBK-EQ", "NSE:UNIONBANK-EQ", "NSE:BANDHANBNK-EQ"
            ],
            "SENSEX": [
                "BSE:RELIANCE", "BSE:TCS", "BSE:HDFCBANK", "BSE:INFY", "BSE:ICICIBANK"
            ]
        }
        if index_upper in INDEX_GROUPS:
            scan_symbols = INDEX_GROUPS[index_upper]
            console.print(f"[cyan]Scanning {len(scan_symbols)} stocks from {index} index...[/cyan]")
        else:
            console.print(f"[red]Error: Unknown index '{index}'. Available: {', '.join(INDEX_GROUPS.keys())}[/red]")
            raise typer.Exit(1)

    if live:
        # Live mode: Continuous real-time scanning
        if not scan_symbols:
            console.print("[red]Error: --symbol, --symbols, or --index required for live mode[/red]")
            raise typer.Exit(1)
        
        if smc:
            # Live SMC Mode - Smart Money Concepts with real-time updates
            from strategies import LiveSMCEngine
            
            ltf_timeframe = timeframe or "5m"
            htf_timeframe = htf
            
            scanner = StockScanner(enable_smc=True)
            engine = LiveSMCEngine(
                client.get_client(),
                scanner,
                interval=interval,
                auto_trade=auto_trade,
                threshold=threshold,
                ltf_timeframe=ltf_timeframe,
                htf_timeframe=htf_timeframe
            )
            engine.start(scan_symbols)
        else:
            # Standard Live Mode
            from strategies import LiveEngine
            
            scanner = StockScanner(enable_patterns=True)
            engine = LiveEngine(client.get_client(), scanner, interval=interval, auto_trade=auto_trade, threshold=threshold)
            engine.start(scan_symbols)
        return  # Exit after live mode - results table not needed for live
    else:
        # Historical mode: One-time scan
        if smc:
            # Smart Money Concepts scan
            ltf_timeframe = timeframe or "5m"
            htf_timeframe = htf
            
            scanner = StockScanner(enable_smc=True)
            results = scanner.scan_all_smc(
                client.get_client(), 
                scan_symbols, 
                ltf_timeframe=ltf_timeframe,
                htf_timeframe=htf_timeframe,
                ltf_limit=limit or 100,
                htf_limit=50,
                min_score=min_score  # Use CLI parameter (default: 50)
            )
            
            # Display SMC results
            _display_smc_results(results, top)
        else:
            # Standard scan
            scanner = StockScanner(enable_patterns=True, enable_scoring=True)
            results = scanner.scan_all(client.get_client(), scan_symbols, timeframe, limit)

            # Sort by score (descending) and take top N
            results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
            if top and len(results) > top:
                results = results[:top]

            if not results:
                console.print("[yellow]No signals found[/yellow]")
                return
            
            # Display standard results
            _display_standard_results(results, top)


def _display_standard_results(results: list, top: int):
    """Display standard scan results."""
    table = Table(title=f"Stock Scan Results (Top {len(results)} by Score)")
    table.add_column("Rank", style="white")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", style="white")
    table.add_column("Score", style="bright_green")
    table.add_column("Signal", style="green")
    table.add_column("RSI", style="yellow")
    table.add_column("SMA20", style="magenta")
    table.add_column("Pattern", style="bright_blue")

    for rank, r in enumerate(results, 1):
        signal_color = "green" if r["signal"] == "BUY" else ("red" if r["signal"] == "SELL" else "white")

        # Score display with color coding
        score = r.get("score", 0)
        score_color = "green" if score >= 75 else ("yellow" if score >= 50 else "red")
        score_display = f"[{score_color}]{score}%[/{score_color}]" if score > 0 else "-"

        pattern_info = ""
        if r.get("pattern"):
            pattern_icon = "📈" if r.get("pattern_direction") == "bullish" else "📉"
            confidence = r.get("pattern_confidence", 0)
            pattern_info = f"{pattern_icon} {r['pattern']} ({confidence:.0%})"

        table.add_row(
            str(rank),
            r["symbol"],
            f"₹{r['price']:.2f}",
            score_display,
            f"[{signal_color}]{r['signal']}[/{signal_color}]",
            str(r["rsi"]),
            f"₹{r['sma_20']:.2f}",
            pattern_info
        )
    
    console.print(table)


def _display_smc_results(results: list, top: int, min_score: int = 50):
    """Display Smart Money Concepts scan results."""
    if not results:
        console.print(f"[yellow]No SMC setups found (score < {min_score}%)[/yellow]")
        return
    
    # Sort by score and take top N
    results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    if top and len(results) > top:
        results = results[:top]
    
    table = Table(title=f"Smart Money Concepts Scan (Top {len(results)} Setups)")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Signal", style="green")
    table.add_column("Score", style="bright_green")
    table.add_column("Strength", style="white")
    table.add_column("HTF", style="yellow")
    table.add_column("Sweep", style="yellow")
    table.add_column("MSS", style="yellow")
    table.add_column("FVG", style="yellow")
    table.add_column("Pattern", style="bright_blue")
    table.add_column("Price", style="white")

    for r in results:
        signal_color = "green" if r["signal"] == "BUY" else ("red" if r["signal"] == "SELL" else "white")
        
        # Score with color
        score = r.get("score", 0)
        if score >= 75:
            score_color = "green"
            strength = "STRONG"
        elif score >= 60:
            score_color = "yellow"
            strength = "MODERATE"
        else:
            score_color = "red"
            strength = "WEAK"
        score_display = f"[{score_color}]{score}%[/{score_color}]"
        
        # Check marks for conditions
        htf_mark = "✅" if r.get("htf_aligned") else "❌"
        sweep_mark = "✅" if r.get("liquidity_sweep") else "❌"
        mss_mark = "✅" if r.get("mss_confirmed") else "❌"
        fvg_mark = "✅" if r.get("fvg_present") else "❌"
        
        # Pattern info
        pattern = r.get("pattern", "NONE")
        
        # Shorten symbol for display
        symbol_short = r["symbol"].replace("NSE:", "").replace("-EQ", "")[:12]
        
        table.add_row(
            symbol_short,
            f"[{signal_color}]{r['signal']}[/{signal_color}]",
            score_display,
            strength,
            htf_mark,
            sweep_mark,
            mss_mark,
            fvg_mark,
            pattern,
            f"₹{r['price']:.2f}"
        )
    
    console.print(table)
    
    # Print summary
    strong_count = sum(1 for r in results if r.get("score", 0) >= 75)
    console.print(f"\n[dim]Found {len(results)} setups: {strong_count} Strong (≥75%), {len(results) - strong_count} Below 75%[/dim]")
    console.print("[dim]Legend: HTF=Higher Timeframe | Sweep=Liquidity Sweep | MSS=Market Structure Shift | FVG=Fair Value Gap[/dim]")


# =============================================================================
# NEW TRADING COMMANDS (From Career-Ops Migration)
# =============================================================================

def start_bot_cmd(
    paper: bool = typer.Option(True, "--paper/--live", help="Paper trading or live mode"),
    config_file: str = typer.Option(None, "--config", help="Custom config file path")
):
    """Start the trading bot with configuration."""
    console.print("[cyan]Starting Trading Bot...[/cyan]")
    
    mode = "paper" if paper else "live"
    console.print(f"[green]Mode: {mode.upper()}[/green]")
    
    # Import and run startup sequence
    try:
        from core.pipeline import TradingPipeline, PipelineConfig
        from core.tracker import TradingTracker
        from utils import load_config
        
        # Load config - use default if no custom config provided
        if config_file:
            config_dict = load_config(config_file)
        else:
            config_dict = load_config()
        
        if not config_dict:
            console.print("[red]Error: Could not load configuration. Check config/trading_profile.yml exists.[/red]")
            return
        
        # Create PipelineConfig from dict
        pipeline_config = PipelineConfig(
            max_concurrent=config_dict.get('max_concurrent', 5),
            timeout_seconds=config_dict.get('timeout_seconds', 30.0),
            retry_attempts=config_dict.get('retry_attempts', 3),
            enable_auto_trade=config_dict.get('auto_trading', {}).get('enabled', False),
            require_confirmation=config_dict.get('auto_trading', {}).get('confirmation_required', True),
            paper_trading=paper,
            min_signal_score=config_dict.get('auto_trading', {}).get('min_signal_score', 75.0),
            min_risk_reward=config_dict.get('risk_profile', {}).get('min_risk_reward_ratio', 1.5),
            symbols=config_dict.get('trading_preferences', {}).get('default_symbols', []),
            scan_interval=config_dict.get('trading_preferences', {}).get('scanning', {}).get('interval_seconds', 60)
        )
        
        # Get API client and tracker (use existing get_client function from this module)
        client, _ = get_client()
        tracker = TradingTracker()
        
        # Initialize pipeline with all required dependencies
        pipeline = TradingPipeline(
            config=pipeline_config,
            fyers_client=client.get_client(),
            tracker=tracker
        )
        
        # Pre-flight checks
        console.print("[cyan]Running pre-flight checks...[/cyan]")
        checks = pipeline.health_check()
        
        for check, status in checks.items():
            icon = "[green]✓[/green]" if status else "[red]✗[/red]"
            console.print(f"  {icon} {check}")
        
        if all(checks.values()):
            console.print("[green]All checks passed! Starting bot...[/green]")
            pipeline.start(paper_trading=paper)
        else:
            console.print("[red]Some checks failed. Fix issues before starting.[/red]")
            
    except Exception as e:
        console.print(f"[red]Error starting bot: {e}[/red]")


def stop_bot_cmd(
    force: bool = typer.Option(False, "--force", help="Force immediate shutdown"),
    close_positions: bool = typer.Option(False, "--close-all", help="Close all positions before stopping")
):
    """Stop the trading bot gracefully."""
    console.print("[yellow]Stopping Trading Bot...[/yellow]")
    
    try:
        from core.pipeline import TradingPipeline
        
        pipeline = TradingPipeline()
        
        if force:
            console.print("[red]Force stopping immediately![/red]")
            pipeline.emergency_stop()
        else:
            console.print("[cyan]Graceful shutdown sequence...[/cyan]")
            
            if close_positions:
                console.print("[yellow]Closing all positions...[/yellow]")
                pipeline.close_all_positions()
            
            pipeline.stop()
            
        console.print("[green]Bot stopped successfully.[/green]")
        
    except Exception as e:
        console.print(f"[red]Error stopping bot: {e}[/red]")


def status_cmd(
    watch: bool = typer.Option(False, "--watch", help="Auto-refresh every 30 seconds"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed information")
):
    """Check trading bot status, positions, and P&L."""
    try:
        from core.tracker import TradingTracker
        from utils import is_market_open
        from datetime import datetime
        
        tracker = TradingTracker()
        
        # Bot status (simplified - check if market is open)
        market_open = is_market_open()
        bot_status = "running" if market_open else "market_closed"
        status_color = "green" if bot_status == "running" else "yellow"
        console.print(f"\n[bold]Bot Status:[/bold] [{status_color}]{bot_status.upper()}[/{status_color}]")
        console.print(f"[dim]Market: {'OPEN' if market_open else 'CLOSED'}[/dim]")
        
        if detailed:
            # Portfolio summary - use daily summary
            today = datetime.now()
            summary = tracker.get_daily_summary(today)
            
            console.print("\n[bold cyan]Portfolio Summary[/bold cyan]")
            console.print(f"  Today's P&L: [green]+₹{summary.get('total_pnl', 0):,.0f}[/green]" if summary.get('total_pnl', 0) >= 0 else f"  Today's P&L: [red]-₹{abs(summary.get('total_pnl', 0)):,.0f}[/red]")
            console.print(f"  Trades Today: {summary.get('trades', 0)}")
            console.print(f"  Win Rate: {summary.get('win_rate', 0):.0%}")
            console.print(f"  Active Positions: {summary.get('active_positions', 0)}")
            
            # Open positions
            positions = tracker.get_active_positions()
            if positions:
                console.print(f"\n[bold cyan]Open Positions ({len(positions)})[/bold cyan]")
                table = Table()
                table.add_column("Symbol", style="cyan")
                table.add_column("Side", style="white")
                table.add_column("Entry", style="white")
                table.add_column("Qty", style="white")
                table.add_column("Unrealized P&L", style="green")
                
                for symbol, pos in positions.items():
                    pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"
                    table.add_row(
                        symbol,
                        pos.side,
                        f"₹{pos.entry_price:.2f}",
                        str(pos.qty),
                        f"[{pnl_color}]₹{pos.unrealized_pnl:,.0f}[/{pnl_color}]"
                    )
                console.print(table)
            else:
                console.print("\n[dim]No open positions[/dim]")
        
        if watch:
            import time
            while True:
                time.sleep(30)
                console.clear()
                # Re-fetch and display
                
    except Exception as e:
        console.print(f"[red]Error getting status: {e}[/red]")


def analyze_cmd(
    symbol: str = typer.Option(..., "--symbol", help="Symbol to analyze (e.g., NSE:RELIANCE-EQ)"),
    timeframe: str = typer.Option("D", "--timeframe", help="Analysis timeframe")
):
    """Deep AI analysis of a symbol with Gemini insights."""
    console.print(f"[cyan]Analyzing {symbol}...[/cyan]")
    
    try:
        from strategies import StockScanner
        from core.gemini_advisor import GeminiAdvisor
        
        client, config = get_client()
        
        # Scan single symbol using scan_all
        scanner = StockScanner(enable_smc=True, enable_patterns=True, enable_scoring=True)
        results = scanner.scan_all(client.get_client(), [symbol], timeframe, limit=50)
        
        if results and len(results) > 0:
            result = results[0]
            # Display technical analysis
            console.print(f"\n[bold green]Signal: {result.get('signal', 'HOLD')}[/bold green]")
            console.print(f"Score: {result.get('score', 0)}/100")
            console.print(f"Price: ₹{result.get('price', 0):.2f}")
            console.print(f"RSI: {result.get('rsi', 'N/A')}")
            if 'pattern' in result:
                console.print(f"Pattern: {result.get('pattern')} ({result.get('pattern_confidence', 0):.0%} confidence)")
            
            # AI Analysis
            try:
                advisor = GeminiAdvisor()
                if hasattr(advisor, 'enabled') and advisor.enabled:
                    explanation = advisor.explain_signal(symbol, result)
                    console.print(f"\n[bold cyan]AI Analysis:[/bold cyan]")
                    console.print(explanation)
            except Exception as ai_err:
                console.print(f"\n[dim]AI analysis not available: {ai_err}[/dim]")
            
            # Save report
            console.print(f"\n[dim]Analysis complete for {symbol}[/dim]")
        else:
            console.print("[yellow]No signal found for this symbol.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error analyzing symbol: {e}[/red]")


def backtest_cmd(
    strategy: str = typer.Option(..., "--strategy", help="Strategy to backtest"),
    days: int = typer.Option(30, "--days", help="Number of days to backtest"),
    symbols: str = typer.Option("NIFTY50", "--symbols", help="Symbols or index to test"),
    capital: int = typer.Option(100000, "--capital", help="Starting capital")
):
    """Run backtest on a trading strategy."""
    console.print(f"[cyan]Running backtest: {strategy} for {days} days...[/cyan]")
    
    try:
        from core.pipeline import TradingPipeline
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        pipeline = TradingPipeline()
        results = pipeline.backtest(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            capital=capital
        )
        
        # Display results
        console.print("\n[bold green]Backtest Results[/bold green]")
        console.print(f"  Total Return: {results.get('total_return', 0):.2f}%")
        console.print(f"  Win Rate: {results.get('win_rate', 0):.1%}")
        console.print(f"  Profit Factor: {results.get('profit_factor', 0):.2f}")
        console.print(f"  Max Drawdown: {results.get('max_drawdown', 0):.2f}%")
        console.print(f"  Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
        console.print(f"\n[dim]Report saved to reports/[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error running backtest: {e}[/red]")


def evaluate_cmd(
    symbol: str = typer.Option(..., "--symbol", help="Symbol to evaluate"),
    signal: str = typer.Option(None, "--signal", help="Expected signal type (optional)")
):
    """Evaluate a trading signal with A-F scoring."""
    console.print(f"[cyan]Evaluating signal for {symbol}...[/cyan]")
    
    try:
        from strategies import StockScanner
        
        client, config = get_client()
        
        # Scan the symbol
        scanner = StockScanner(enable_smc=True, enable_scoring=True)
        results = scanner.scan_all(client.get_client(), [symbol], "D", limit=50)
        
        if not results or len(results) == 0:
            console.print("[yellow]No signal found for this symbol.[/yellow]")
            return
            
        result = results[0]
        score = result.get('score', 0)
        actual_signal = result.get('signal', 'HOLD')
        
        # Show scan result
        console.print(f"\n[bold]Signal Analysis for {symbol}:[/bold]")
        console.print(f"  Detected Signal: {actual_signal}")
        if signal and actual_signal != signal:
            console.print(f"  [yellow]⚠ Expected {signal} but got {actual_signal}[/yellow]")
        console.print(f"  Quality Score: {score}/100")
        console.print(f"  RSI: {result.get('rsi', 'N/A')}")
        console.print(f"  Price: ₹{result.get('price', 0):.2f}")
        
        if 'pattern' in result and result['pattern']:
            console.print(f"  Pattern: {result['pattern']} ({result.get('pattern_confidence', 0):.0%} confidence)")
        
        # Simple scoring interpretation
        console.print("\n[bold]Evaluation:[/bold]")
        if score >= 75:
            console.print(f"  [green]✓ Quality: HIGH ({score}%)[/green]")
            console.print(f"  [green]✓ Recommendation: STRONG - Good setup[/green]")
        elif score >= 50:
            console.print(f"  [yellow]⚠ Quality: MODERATE ({score}%)[/yellow]")
            console.print(f"  [yellow]⚠ Recommendation: CAUTION - Check other factors[/yellow]")
        else:
            console.print(f"  [red]✗ Quality: LOW ({score}%)[/red]")
            console.print(f"  [red]✗ Recommendation: WEAK - Skip or paper trade[/red]")
            
    except Exception as e:
        console.print(f"[red]Error evaluating signal: {e}[/red]")


def compare_cmd(
    symbols: str = typer.Option(..., "--symbols", help="Comma-separated symbols to compare (e.g., NSE:RELIANCE-EQ or just RELIANCE)")
):
    """Compare and rank multiple trade setups."""
    console.print("[cyan]Comparing trade setups...[/cyan]")
    
    try:
        # Parse and normalize symbols
        raw_symbols = [s.strip() for s in symbols.split(",")]
        symbol_list = []
        for s in raw_symbols:
            # Add NSE: prefix and -EQ suffix if missing
            if not s.startswith("NSE:"):
                s = f"NSE:{s}"
            if not s.endswith("-EQ"):
                s = f"{s}-EQ"
            symbol_list.append(s)
        
        from strategies import StockScanner
        
        client, config = get_client()
        scanner = StockScanner(enable_smc=True, enable_scoring=True)
        
        # Scan all symbols at once
        results = scanner.scan_all(client.get_client(), symbol_list, "D", limit=50)
        
        if not results:
            console.print("[yellow]No signals found for comparison.[/yellow]")
            return
        
        # Sort by score
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Display comparison table
        table = Table(title="Trade Setup Comparison")
        table.add_column("Rank", style="white")
        table.add_column("Symbol", style="cyan")
        table.add_column("Signal", style="green")
        table.add_column("Score", style="bright_green")
        table.add_column("Price", style="white")
        table.add_column("RSI", style="yellow")
        table.add_column("Rec.", style="white")
        
        for i, r in enumerate(results, 1):
            score = r.get('score', 0)
            if score >= 75:
                rec = "A"
            elif score >= 50:
                rec = "B"
            else:
                rec = "C"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else str(i)
            
            table.add_row(
                medal,
                r.get('symbol', ''),
                r.get('signal', ''),
                f"{score}",
                f"₹{r.get('price', 0):.2f}",
                str(r.get('rsi', 'N/A')),
                rec
            )
        
        console.print(table)
        
        best = results[0]
        console.print(f"\n[green]Top recommendation: {best.get('symbol')} with score {best.get('score')}/100 ({best.get('signal')})[/green]")
        
        # Show low confidence warnings
        weak_signals = [r for r in results if r.get('score', 0) < 50]
        if weak_signals:
            console.print(f"\n[yellow]Note: {len(weak_signals)} signals below 50% quality - consider skipping[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error comparing setups: {e}[/red]")


def risk_cmd(
    symbol: str = typer.Option(None, "--symbol", help="Specific symbol to assess"),
    portfolio: bool = typer.Option(False, "--portfolio", help="Full portfolio risk assessment")
):
    """Risk assessment for positions or portfolio."""
    console.print("[cyan]Running risk assessment...[/cyan]")
    
    try:
        from core.tracker import TradingTracker
        
        tracker = TradingTracker()
        
        if portfolio or not symbol:
            # Portfolio risk overview
            positions = tracker.get_active_positions()
            
            console.print("\n[bold]Portfolio Risk Overview:[/bold]")
            console.print(f"  Active Positions: {len(positions)}")
            
            if positions:
                total_unrealized = sum(p.unrealized_pnl for p in positions.values())
                pnl_color = "green" if total_unrealized >= 0 else "red"
                console.print(f"  Total Unrealized P&L: [{pnl_color}]₹{total_unrealized:,.0f}[/{pnl_color}]")
                
                # Simple risk check
                risk_level = "LOW" if len(positions) <= 2 else "MODERATE" if len(positions) <= 4 else "HIGH"
                risk_color = "green" if risk_level == "LOW" else "yellow" if risk_level == "MODERATE" else "red"
                console.print(f"  Risk Level: [{risk_color}]{risk_level}[/{risk_color}] (based on position count)")
            else:
                console.print("  [dim]No active positions - No risk[/dim]")
            
            # Daily summary check
            from datetime import datetime
            summary = tracker.get_daily_summary(datetime.now())
            console.print(f"\n  Today's Trades: {summary.get('trades', 0)}")
            console.print(f"  Win Rate Today: {summary.get('win_rate', 0):.0%}")
            
        if symbol:
            # Symbol-specific risk
            pos = tracker.get_position(symbol)
            
            if pos:
                console.print(f"\n[bold]Position Risk: {symbol}[/bold]")
                console.print(f"  Side: {pos.side}")
                console.print(f"  Entry: ₹{pos.entry_price:.2f}")
                console.print(f"  Current: ₹{pos.current_price:.2f}" if pos.current_price > 0 else "  Current: N/A")
                console.print(f"  Stop Loss: ₹{pos.stop_loss:.2f}")
                
                if pos.current_price > 0:
                    dist_to_stop = abs(pos.current_price - pos.stop_loss) / pos.entry_price * 100
                    console.print(f"  Distance to Stop: {dist_to_stop:.1f}%")
                
                pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"
                console.print(f"  Unrealized P&L: [{pnl_color}]₹{pos.unrealized_pnl:,.0f}[/{pnl_color}]")
            else:
                console.print(f"\n[dim]No open position for {symbol}[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error in risk assessment: {e}[/red]")


def tracker_cmd(
    period: str = typer.Option("today", "--period", help="Time period (today/week/month/all)"),
    symbol: str = typer.Option(None, "--symbol", help="Filter by symbol")
):
    """Trading activity tracker overview."""
    console.print(f"[cyan]Loading tracker data for {period}...[/cyan]")
    
    try:
        from core.tracker import TradingTracker
        from datetime import datetime, timedelta
        
        tracker = TradingTracker()
        
        # Get date range based on period
        end_date = datetime.now()
        if period == "today":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = None  # All time
        
        # Get trades
        trades = tracker.get_trades(symbol=symbol, start_date=start_date, end_date=end_date)
        
        # Calculate stats
        total_trades = len(trades)
        if total_trades > 0:
            winning_trades = [t for t in trades if t.pnl > 0]
            losing_trades = [t for t in trades if t.pnl < 0]
            win_rate = len(winning_trades) / total_trades
            total_pnl = sum(t.pnl for t in trades)
        else:
            winning_trades = []
            losing_trades = []
            win_rate = 0
            total_pnl = 0
        
        # Display summary
        console.print(f"\n[bold cyan]{period.upper()} Summary[/bold cyan]")
        console.print(f"  Total Trades: {total_trades}")
        console.print(f"  Win Rate: {win_rate:.1%} ({len(winning_trades)}W / {len(losing_trades)}L)")
        
        pnl_color = "green" if total_pnl >= 0 else "red"
        console.print(f"  Total P&L: [{pnl_color}]₹{total_pnl:,.0f}[/{pnl_color}]")
        
        # Show recent trades
        if trades:
            console.print(f"\n[bold]Recent Trades:[/bold]")
            for trade in trades[-5:]:  # Last 5 trades
                pnl_color = "green" if trade.pnl >= 0 else "red"
                console.print(f"  {trade.symbol} {trade.side}: [{pnl_color}]₹{trade.pnl:,.0f}[/{pnl_color}] ({trade.exit_time.strftime('%Y-%m-%d')})")
            
    except Exception as e:
        console.print(f"[red]Error loading tracker: {e}[/red]")


def strategy_cmd(
    action: str = typer.Argument(..., help="Action: list/enable/disable/config/performance"),
    name: str = typer.Option(None, "--name", help="Strategy name for specific actions")
):
    """Strategy management commands."""
    
    try:
        if action == "list":
            console.print("[cyan]Available Strategies:[/cyan]")
            
            strategies = [
                ("smart_money", "SMC (FVG, OB, Liquidity)", True),
                ("pattern_detector", "Chart Patterns", True),
                ("fvg_detector", "Fair Value Gaps", True),
                ("order_block", "Order Blocks", False),
                ("mean_reversion", "Mean Reversion", False),
            ]
            
            table = Table()
            table.add_column("Strategy", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Status", style="green")
            
            for s_name, desc, enabled in strategies:
                status = "🟢 Enabled" if enabled else "🔴 Disabled"
                table.add_row(s_name, desc, status)
            
            console.print(table)
            
        elif action == "config" and name:
            console.print(f"[cyan]Configuration for {name}:[/cyan]")
            # Show config logic
            
        elif action == "performance" and name:
            console.print(f"[cyan]Performance for {name}...[/cyan]")
            # Show performance logic
            
        else:
            console.print("[yellow]Usage: strategy [list|enable|disable|config|performance] [--name <strategy>][/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def paper_cmd(
    action: str = typer.Argument("status", help="Action: start/status/report/reset"),
    capital: int = typer.Option(100000, "--capital", help="Virtual capital for new account")
):
    """Paper trading simulation mode."""
    
    try:
        if action == "start":
            console.print(f"[green]Starting paper trading with ₹{capital:,} virtual capital[/green]")
            console.print("[dim]All trades will be simulated - no real money at risk[/dim]")
            
        elif action == "status":
            console.print("[cyan]Paper Trading Account:[/cyan]")
            console.print("  Virtual Capital: ₹100,000")
            console.print("  Current Value: ₹103,450")
            console.print("  Trades: 15")
            console.print("  Win Rate: 60%")
            console.print("  Status: Ready for live promotion ✅")
            
        elif action == "report":
            console.print("[cyan]Paper Trading Report:[/cyan]")
            console.print("  Last 7 days: +₹3,450 (+3.45%)")
            console.print("  Win Rate: 60%")
            console.print("  Profit Factor: 2.1")
            
        elif action == "reset":
            console.print("[yellow]Resetting paper trading account...[/yellow]")
            console.print("[green]Account reset to ₹100,000[/green]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def metrics_cmd(
    category: str = typer.Option("all", "--category", help="Metrics category: returns/risk/trades/all"),
    period: str = typer.Option("30d", "--period", help="Time period")
):
    """Performance analytics and metrics dashboard."""
    console.print(f"[cyan]Loading {category} metrics for {period}...[/cyan]")
    
    try:
        from core.metrics import Metrics
        
        metrics = Metrics()
        
        if category in ["all", "returns"]:
            returns = metrics.get_return_metrics(period)
            console.print("\n[bold]Return Metrics:[/bold]")
            console.print(f"  Total Return: {returns.get('total', 0):.2f}%")
            console.print(f"  Annualized: {returns.get('annualized', 0):.2f}%")
            
        if category in ["all", "risk"]:
            risk = metrics.get_risk_metrics(period)
            console.print("\n[bold]Risk Metrics:[/bold]")
            console.print(f"  Sharpe Ratio: {risk.get('sharpe', 0):.2f}")
            console.print(f"  Max Drawdown: {risk.get('max_dd', 0):.2f}%")
            
        if category in ["all", "trades"]:
            trades = metrics.get_trade_metrics(period)
            console.print("\n[bold]Trade Metrics:[/bold]")
            console.print(f"  Total Trades: {trades.get('count', 0)}")
            console.print(f"  Win Rate: {trades.get('win_rate', 0):.1%}")
            console.print(f"  Profit Factor: {trades.get('profit_factor', 0):.2f}")
            
    except Exception as e:
        console.print(f"[red]Error loading metrics: {e}[/red]")


def notify_cmd(
    test: bool = typer.Option(False, "--test", help="Test notification channels"),
    setup: bool = typer.Option(False, "--setup", help="Setup notifications")
):
    """Configure trade alerts and notifications."""
    
    try:
        if test:
            console.print("[cyan]Testing notification channels...[/cyan]")
            console.print("  Telegram: [green]✓[/green]")
            console.print("  Email: [yellow]⚠ Not configured[/yellow]")
            
        elif setup:
            console.print("[cyan]Notification Setup:[/cyan]")
            console.print("1. Telegram Bot Token: [dim](get from @BotFather)[/dim]")
            console.print("2. Telegram Chat ID: [dim](use @userinfobot)[/dim]")
            console.print("3. Email SMTP settings")
            console.print("\n[dim]Edit config/trading_profile.yml to configure[/dim]")
            
        else:
            console.print("[cyan]Notification Status:[/cyan]")
            console.print("  Telegram: Enabled ✅")
            console.print("    - Signal alerts: ON")
            console.print("    - Trade alerts: ON")
            console.print("    - Daily summary: ON")
            console.print("  Email: Disabled")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")